"""Backtesting API controller."""

import logging
import uuid
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
import csv
import io
import os
from datetime import datetime

from ...application.backtesting import (
    RunBacktestUseCase,
    GetBacktestUseCase,
    ListBacktestsUseCase,
    GetBacktestResultsUseCase,
    CancelBacktestUseCase,
    DeleteBacktestUseCase,
)
from ...application.backtesting.schemas import (
    RunBacktestRequest,
    BacktestRunResponse,
    BacktestResultsResponse,
    BacktestListResponse,
    BacktestStatusResponse,
)
from ...domain.backtesting import BacktestConfig, BacktestRun
from ...domain.exchange import ExchangeType
from ...infrastructure.backtesting import BacktestRepository
from ...infrastructure.persistence.database import get_db
from ...infrastructure.exchange.binance_adapter import BinanceAdapter
from ...infrastructure.services.market_data_service import MarketDataService
from ...infrastructure.repositories.exchange_repository import ExchangeRepository
from ...infrastructure.persistence.repositories.market_data_repository import CandleRepository, MarketMetadataRepository
from ...domain.market_data.gap_detector import GapDetector
from ...domain.user import User
from ...interfaces.dependencies.auth import get_current_active_user


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/backtests", tags=["backtests"])


# Dependency injection helpers
async def get_backtest_repository(
    db: AsyncSession = Depends(get_db)
) -> BacktestRepository:
    """Get backtest repository."""
    return BacktestRepository(db)


def get_current_user_id(user: User = Depends(get_current_active_user)) -> UUID:
    """Get current user ID from auth."""
    return user.id



@router.post("", response_model=BacktestRunResponse, status_code=202)
async def run_backtest(
    request: RunBacktestRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    repository: BacktestRepository = Depends(get_backtest_repository),
):
    """
    Start a new backtest run.
    
    The backtest will run in the background. Use the returned ID to check status and results.
    """
    
    try:
        user_id = current_user.id
        
        # Convert request to domain config
        config = BacktestConfig(
            symbol=request.config.symbol,  # Add symbol to config
            mode=request.config.mode.value if hasattr(request.config.mode, 'value') else request.config.mode,
            initial_capital=request.config.initial_capital,
            position_sizing=request.config.position_sizing.value if hasattr(request.config.position_sizing, 'value') else request.config.position_sizing,
            position_size_value=request.config.position_size_percent / 100,  # Convert percent to decimal
            max_position_size=request.config.max_position_size,
            slippage_model=request.config.slippage_model.value if hasattr(request.config.slippage_model, 'value') else request.config.slippage_model,
            slippage_percent=request.config.slippage_percent / 100,  # Convert percent to decimal
            commission_model=request.config.commission_model.value if hasattr(request.config.commission_model, 'value') else request.config.commission_model,
            commission_percent=request.config.commission_rate / 100,  # API uses commission_rate, convert to percent
        )
        
        # Load strategy function dynamically based on strategy_id
        from ...strategies.backtest_adapter import get_strategy_function
        
        # Get strategy parameters from config if available
        strategy_config = getattr(request.config, 'strategy_params', None) or {}
        
        strategy_func = get_strategy_function(
            strategy_id=str(request.strategy_id),
            config=strategy_config
        )
        
        logger.info(f"Loaded strategy function for ID: {request.strategy_id}")
        
        # Lookup exchange connection and create appropriate adapter
        exchange_repo = ExchangeRepository(repository._session)
        exchange_connection = await exchange_repo.find_by_id(request.exchange_connection_id)
        
        if not exchange_connection:
            raise HTTPException(
                status_code=400, 
                detail=f"Exchange connection {request.exchange_connection_id} not found"
            )
        
        # Verify the connection belongs to the user
        if exchange_connection.user_id != user_id:
            raise HTTPException(
                status_code=403, 
                detail="Not authorized to use this exchange connection"
            )
        
        # Get API credentials from connection
        api_key = exchange_connection.credentials.api_key
        api_secret = exchange_connection.credentials.secret_key
        is_testnet = exchange_connection.is_testnet
        
        # Create adapter based on exchange type
        if exchange_connection.exchange_type == ExchangeType.BINANCE:
            adapter = BinanceAdapter(api_key=api_key, api_secret=api_secret, testnet=is_testnet)
        else:
            # For unsupported exchanges, raise error
            raise HTTPException(
                status_code=400,
                detail=f"Exchange type {exchange_connection.exchange_type} not yet supported for backtesting"
            )
        
        # Instantiate dependencies for MarketDataService
        candle_repo = CandleRepository(repository._session)
        metadata_repo = MarketMetadataRepository(repository._session)
        gap_detector = GapDetector()
        
        market_data_service = MarketDataService(
            exchange_adapter=adapter,
            candle_repository=candle_repo,
            metadata_repository=metadata_repo,
            gap_detector=gap_detector
        )
        
        use_case = RunBacktestUseCase(repository, market_data_service)

        
        # Create backtest run entity FIRST (before background task)
    # Create BacktestRun entity
        backtest_id = uuid.uuid4()
        backtest_run = BacktestRun(
            id=backtest_id,
            user_id=current_user.id,
            strategy_id=request.strategy_id,
            exchange_connection_id=request.exchange_connection_id,
            exchange_name=exchange_connection.name,
            symbol=request.config.symbol,
            timeframe=request.config.timeframe,
            start_date=request.config.start_date,
            end_date=request.config.end_date,
            config=config,
        )

        await repository.save(backtest_run)
        backtest_id = backtest_run.id
        
        # Run in background - use existing backtest_run
        async def run_backtest_task():
            logger.info(f"Task started for backtest {backtest_id}")
            try:
                result = await use_case.execute(
                    user_id=user_id,
                    strategy_id=request.strategy_id,
                    config=config,
                    symbol=request.config.symbol,
                    timeframe=request.config.timeframe,
                    start_date=request.config.start_date,
                    end_date=request.config.end_date,
                    strategy_func=strategy_func,
                    backtest_run_id=backtest_id,  # Pass ID to prevent duplicate creation
                )
                logger.info(f"Task completed for backtest {backtest_id}")
            except Exception as e:
                logger.error(f"Backtest task failed: {str(e)}")
                import traceback
                traceback.print_exc()
        
        
        
        
        
        background_tasks.add_task(run_backtest_task)
        
        # Return the backtest_run that was already created
        return BacktestRunResponse.model_validate(backtest_run)
        
    except Exception as e:
        logger.error(f"Failed to start backtest: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{backtest_id}", response_model=BacktestRunResponse)
async def get_backtest(
    backtest_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    repository: BacktestRepository = Depends(get_backtest_repository),
):
    """Get backtest run by ID."""
    
    use_case = GetBacktestUseCase(repository)
    backtest_run = await use_case.execute(backtest_id)
    
    if not backtest_run:
        raise HTTPException(status_code=404, detail="Backtest not found")
    
    # Verify ownership
    if backtest_run.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    return BacktestRunResponse.model_validate(backtest_run)


@router.get("", response_model=BacktestListResponse)
async def list_backtests(
    strategy_id: Optional[UUID] = Query(None, description="Filter by strategy"),
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user_id: UUID = Depends(get_current_user_id),
    repository: BacktestRepository = Depends(get_backtest_repository),
):
    """List backtests with optional filters."""
    
    use_case = ListBacktestsUseCase(repository)
    backtests = await use_case.execute(
        user_id=user_id,
        strategy_id=strategy_id,
        symbol=symbol,
        limit=limit,
        offset=offset,
    )
    
    total = await repository.count_by_user(user_id)
    
    return BacktestListResponse(
        backtests=[BacktestRunResponse.model_validate(b) for b in backtests],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{backtest_id}/results", response_model=BacktestResultsResponse)
async def get_backtest_results(
    backtest_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    repository: BacktestRepository = Depends(get_backtest_repository),
):
    """Get detailed backtest results with performance metrics."""
    
    # results_service is not needed as repository handles retrieval
    use_case = GetBacktestResultsUseCase(repository, None)
    
    result = await use_case.execute(backtest_id)
    
    if not result:
        raise HTTPException(status_code=404, detail="Backtest not found")
    
    backtest_run = result["backtest_run"]
    
    # Verify ownership
    if backtest_run.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    if not result.get("results"):
        raise HTTPException(
            status_code=400,
            detail=result.get("message", "Results not available")
        )
    
    return BacktestResultsResponse.model_validate(result["results"])


@router.get("/{backtest_id}/status", response_model=BacktestStatusResponse)
async def get_backtest_status(
    backtest_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    repository: BacktestRepository = Depends(get_backtest_repository),
):
    """Get backtest execution status."""
    
    use_case = GetBacktestUseCase(repository)
    backtest_run = await use_case.execute(backtest_id)
    
    if not backtest_run:
        raise HTTPException(status_code=404, detail="Backtest not found")
    
    # Verify ownership
    if backtest_run.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    return BacktestStatusResponse(
        id=backtest_run.id,
        status=backtest_run.status,
        progress_percent=backtest_run.progress_percent,
        message=backtest_run.error_message if backtest_run.error_message else None,
    )


@router.post("/{backtest_id}/cancel", response_model=BacktestStatusResponse)
async def cancel_backtest(
    backtest_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    repository: BacktestRepository = Depends(get_backtest_repository),
):
    """Cancel a running backtest."""
    
    use_case = CancelBacktestUseCase(repository)
    
    try:
        success = await use_case.execute(backtest_id, user_id)
        
        if not success:
            raise HTTPException(
                status_code=400,
                detail="Cannot cancel backtest (not running or not found)"
            )
        
        # Get updated status
        backtest_run = await repository.get_by_id(backtest_id)
        
        return BacktestStatusResponse(
            id=backtest_run.id,
            status=backtest_run.status,
            progress_percent=backtest_run.progress_percent,
            message="Backtest cancelled",
        )
        
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to cancel backtest: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{backtest_id}", status_code=204)
async def delete_backtest(
    backtest_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    repository: BacktestRepository = Depends(get_backtest_repository),
):
    """Delete a backtest run and its results."""
    
    use_case = DeleteBacktestUseCase(repository)
    
    try:
        success = await use_case.execute(backtest_id, user_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Backtest not found")
        
        return None
        
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to delete backtest: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== PHASE 3 INTEGRATION ENDPOINTS =====

@router.get("/{backtest_id}/trades")
async def get_backtest_trades(
    backtest_id: UUID,
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(100, ge=1, le=10000, description="Items per page (max 10000 for chart visualization)"),
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    side: Optional[str] = Query(None, description="Filter by side (buy/sell)"),
    min_pnl: Optional[float] = Query(None, description="Minimum P&L filter"),
    max_pnl: Optional[float] = Query(None, description="Maximum P&L filter"),
    user_id: UUID = Depends(get_current_user_id),
    repository: BacktestRepository = Depends(get_backtest_repository),
):
    """
    Get detailed trade history for a backtest.
    
    Returns paginated list of all trades executed during the backtest
    with filtering options for analysis.
    """
    
    # Verify backtest exists and ownership
    use_case = GetBacktestUseCase(repository)
    backtest_run = await use_case.execute(backtest_id)
    
    if not backtest_run:
        raise HTTPException(status_code=404, detail="Backtest not found")
    
    if backtest_run.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    try:
        # Get trades with filters
        trades = await repository.get_backtest_trades(
            backtest_id=backtest_id,
            page=page,
            limit=limit,
            symbol=symbol,
            side=side,
            min_pnl=min_pnl,
            max_pnl=max_pnl
        )
        
        # Get total count for pagination
        total_count = await repository.count_backtest_trades(
            backtest_id=backtest_id,
            symbol=symbol,
            side=side,
            min_pnl=min_pnl,
            max_pnl=max_pnl
        )
        
        return {
            "trades": [
                {
                    "id": str(trade.id),
                    "symbol": trade.symbol,
                    "side": trade.direction,
                    "entry_price": float(trade.entry_price),
                    "exit_price": float(trade.exit_price) if trade.exit_price else None,
                    "quantity": float(trade.quantity),
                    "pnl": float(trade.net_pnl) if trade.net_pnl is not None else None,
                    "pnl_pct": float(trade.pnl_percent) if trade.pnl_percent is not None else None,
                    "duration": trade.duration_seconds if hasattr(trade, 'duration_seconds') else None,
                    "entry_time": trade.entry_time.isoformat() if trade.entry_time else None,
                    "exit_time": trade.exit_time.isoformat() if trade.exit_time else None,
                }
                for trade in trades
            ],
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total_count,
                "pages": (total_count + limit - 1) // limit
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get backtest trades: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{backtest_id}/equity-curve")
async def get_backtest_equity_curve(
    backtest_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    repository: BacktestRepository = Depends(get_backtest_repository),
):
    """
    Get equity curve data for backtest visualization.
    
    Returns time-series data showing portfolio equity and drawdown over time.
    """
    
    # Verify backtest exists and ownership
    use_case = GetBacktestUseCase(repository)
    backtest_run = await use_case.execute(backtest_id)
    
    if not backtest_run:
        raise HTTPException(status_code=404, detail="Backtest not found")
    
    if backtest_run.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    try:
        # Get equity curve data
        equity_points = await repository.get_equity_curve(backtest_id)
        
        return [
            {
                "timestamp": point.timestamp if isinstance(point.timestamp, str) else point.timestamp.isoformat(),
                "equity": float(point.equity),
                "drawdown": float(point.drawdown_pct) if hasattr(point, 'drawdown_pct') else 0.0
            }
            for point in equity_points
        ]
        
    except Exception as e:
        logger.error(f"Failed to get equity curve: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{backtest_id}/positions")
async def get_backtest_positions(
    backtest_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    repository: BacktestRepository = Depends(get_backtest_repository),
):
    """
    Get position timeline for backtest analysis.
    
    Returns historical data showing open positions, exposure, and margin usage over time.
    """
    
    # Verify backtest exists and ownership
    use_case = GetBacktestUseCase(repository)
    backtest_run = await use_case.execute(backtest_id)
    
    if not backtest_run:
        raise HTTPException(status_code=404, detail="Backtest not found")
    
    if backtest_run.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    try:
        # Get position timeline data
        position_timeline = await repository.get_position_timeline(backtest_id)
        
        return [
            {
                "timestamp": point.timestamp.isoformat(),
                "open_positions": point.open_positions_count,
                "total_exposure": float(point.total_exposure),
                "margin_used": float(point.margin_used) if hasattr(point, 'margin_used') else 0.0,
                "unrealized_pnl": float(point.unrealized_pnl) if hasattr(point, 'unrealized_pnl') else 0.0
            }
            for point in position_timeline
        ]
        
    except Exception as e:
        logger.error(f"Failed to get position timeline: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{backtest_id}/export/csv")
async def export_backtest_csv(
    backtest_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    repository: BacktestRepository = Depends(get_backtest_repository),
):
    """
    Export backtest results as CSV file.
    
    Streams a CSV file containing all trade data for the backtest.
    Useful for external analysis and record keeping.
    """
    
    # Verify backtest exists and ownership
    use_case = GetBacktestUseCase(repository)
    backtest_run = await use_case.execute(backtest_id)
    
    if not backtest_run:
        raise HTTPException(status_code=404, detail="Backtest not found")
    
    if backtest_run.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    try:
        async def generate_csv():
            """Generate CSV data as a stream."""
            
            # Create CSV headers
            headers = [
                "Date", "Symbol", "Side", "Entry Price", "Exit Price",
                "Quantity", "P&L", "P&L%", "Duration (mins)", "Entry Time", "Exit Time"
            ]
            
            # Create in-memory CSV
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(headers)
            yield output.getvalue()
            output.seek(0)
            output.truncate(0)
            
            # Stream trades in batches to handle large datasets
            page = 1
            batch_size = 1000
            
            while True:
                trades = await repository.get_backtest_trades(
                    backtest_id=backtest_id,
                    page=page,
                    limit=batch_size
                )
                
                if not trades:
                    break
                
                for trade in trades:
                    duration_mins = None
                    if hasattr(trade, 'entry_time') and hasattr(trade, 'exit_time') and trade.exit_time:
                        duration = trade.exit_time - trade.entry_time
                        duration_mins = duration.total_seconds() / 60
                    
                    row = [
                        trade.created_at.strftime('%Y-%m-%d'),
                        trade.symbol,
                        trade.side,
                        float(trade.entry_price),
                        float(trade.exit_price) if trade.exit_price else '',
                        float(trade.quantity),
                        float(trade.pnl) if trade.pnl else '',
                        f"{float(trade.pnl_pct):.2f}%" if trade.pnl_pct else '',
                        f"{duration_mins:.1f}" if duration_mins else '',
                        trade.entry_time.strftime('%Y-%m-%d %H:%M:%S') if hasattr(trade, 'entry_time') else '',
                        trade.exit_time.strftime('%Y-%m-%d %H:%M:%S') if hasattr(trade, 'exit_time') and trade.exit_time else ''
                    ]
                    
                    writer.writerow(row)
                
                yield output.getvalue()
                output.seek(0)
                output.truncate(0)
                
                page += 1
        
        # Create filename with timestamp
        filename = f"backtest_{backtest_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        return StreamingResponse(
            generate_csv(),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        logger.error(f"Failed to export backtest CSV: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
