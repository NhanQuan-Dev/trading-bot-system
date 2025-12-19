"""Backtesting API controller."""

import logging
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
import csv
import io
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
from ...domain.backtesting import BacktestConfig
from ...infrastructure.backtesting import BacktestRepository
from ...infrastructure.persistence.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/backtests", tags=["backtests"])


# Dependency injection helpers
async def get_backtest_repository(
    db: AsyncSession = Depends(get_db)
) -> BacktestRepository:
    """Get backtest repository."""
    return BacktestRepository(db)


# Mock user ID (replace with actual auth)
def get_current_user_id() -> UUID:
    """Get current user ID from auth."""
    # TODO: Replace with actual auth
    return UUID("00000000-0000-0000-0000-000000000001")


@router.post("", response_model=BacktestRunResponse, status_code=202)
async def run_backtest(
    request: RunBacktestRequest,
    background_tasks: BackgroundTasks,
    user_id: UUID = Depends(get_current_user_id),
    repository: BacktestRepository = Depends(get_backtest_repository),
):
    """
    Start a new backtest run.
    
    The backtest will run in the background. Use the returned ID to check status and results.
    """
    
    try:
        # Convert request to domain config
        # BacktestConfig doesn't accept symbol/timeframe/dates, those are part of BacktestRun
        config = BacktestConfig(
            mode=request.config.mode.value if hasattr(request.config.mode, 'value') else request.config.mode,
            initial_capital=request.config.initial_capital,
            position_sizing=request.config.position_sizing.value if hasattr(request.config.position_sizing, 'value') else request.config.position_sizing,
            position_size_value=request.config.position_size_percent / 100,  # Convert percent to decimal
            max_position_size=request.config.max_position_size,
            slippage_model=request.config.slippage_model.value if hasattr(request.config.slippage_model, 'value') else request.config.slippage_model,
            slippage_percent=request.config.slippage_percent / 100,  # Convert percent to decimal
            commission_model=request.config.commission_model.value if hasattr(request.config.commission_model, 'value') else request.config.commission_model,
            commission_percent=request.config.commission_rate / 100,  # Convert percent to decimal
        )
        
        # TODO: Load strategy function from strategy_id
        # For now, use a simple moving average crossover strategy
        def strategy_func(candle, idx, position):
            """Simple MA crossover strategy."""
            if idx < 20:
                return None
            
            # Simple signal generation (placeholder)
            if candle.get("close", 0) > candle.get("ma_20", 0):
                if not position:
                    return {"type": "buy"}
            else:
                if position:
                    return {"type": "close"}
            
            return None
        
        # Create use case
        # TODO: Inject proper market data service
        market_data_service = None  # Placeholder
        use_case = RunBacktestUseCase(repository, market_data_service)
        
        # Run in background
        async def run_backtest_task():
            try:
                await use_case.execute(
                    user_id=user_id,
                    strategy_id=request.strategy_id,
                    config=config,
                    strategy_func=strategy_func,
                )
            except Exception as e:
                logger.error(f"Background backtest failed: {str(e)}")
        
        background_tasks.add_task(run_backtest_task)
        
        # Return initial run info
        from ...domain.backtesting import BacktestRun
        backtest_run = BacktestRun(
            user_id=user_id,
            strategy_id=request.strategy_id,
            config=config,
        )
        await repository.save(backtest_run)
        
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
    
    # TODO: Implement results service
    results_service = None  # Placeholder
    use_case = GetBacktestResultsUseCase(repository, results_service)
    
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
    limit: int = Query(100, ge=1, le=500, description="Items per page"),
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
                    "id": trade.id,
                    "symbol": trade.symbol,
                    "side": trade.side,
                    "entry_price": float(trade.entry_price),
                    "exit_price": float(trade.exit_price) if trade.exit_price else None,
                    "quantity": float(trade.quantity),
                    "pnl": float(trade.pnl) if trade.pnl else None,
                    "pnl_pct": float(trade.pnl_pct) if trade.pnl_pct else None,
                    "duration": trade.duration_seconds if hasattr(trade, 'duration_seconds') else None,
                    "created_at": trade.created_at.isoformat(),
                    "entry_time": trade.entry_time.isoformat() if hasattr(trade, 'entry_time') else None,
                    "exit_time": trade.exit_time.isoformat() if hasattr(trade, 'exit_time') and trade.exit_time else None,
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
                "timestamp": point.timestamp.isoformat(),
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
