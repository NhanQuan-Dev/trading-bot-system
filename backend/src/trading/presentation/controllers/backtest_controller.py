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
import asyncio
import multiprocessing
from concurrent.futures import ProcessPoolExecutor
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
    BacktestPeriodStatsResponse,
    PeriodProfitStats,
    PeriodTradeStats,
)
from ...domain.backtesting import BacktestConfig, BacktestRun
from ...domain.exchange import ExchangeType
from ...infrastructure.backtesting import BacktestRepository
from ...infrastructure.persistence.database import get_db, get_db_context
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


# === ProcessPoolExecutor for CPU-bound backtests ===
# This allows running backtest simulations in separate processes,
# preventing them from blocking the main asyncio event loop.
_backtest_executor: ProcessPoolExecutor | None = None


def get_backtest_executor() -> ProcessPoolExecutor:
    """Get or create the global backtest executor."""
    global _backtest_executor
    if _backtest_executor is None:
        # Leave 2 cores for the API server
        max_workers = max(1, multiprocessing.cpu_count() - 2)
        logger.info(f"Initializing BacktestExecutor with {max_workers} workers")
        _backtest_executor = ProcessPoolExecutor(max_workers=max_workers)
    return _backtest_executor


async def run_backtest_in_executor(backtest_id: UUID, user_id: UUID, strategy_id: UUID, 
                                    config_dict: dict, symbol: str, timeframe: str,
                                    start_date: datetime, end_date: datetime,
                                    strategy_name: str, strategy_code: str | None,
                                    exchange_type: str, is_testnet: bool):
    """
    Run backtest execution in a separate process via ProcessPoolExecutor.
    This function is called from the background task and handles all the heavy work.
    """
    # Import here to avoid circular imports and ensure fresh module state per process
    async with get_db_context() as session:
        logger.info(f"Executor task started for backtest {backtest_id}")
        
        # Re-instantiate dependencies with NEW session
        task_repo = BacktestRepository(session)
        task_candle_repo = CandleRepository(session)
        task_metadata_repo = MarketMetadataRepository(session)
        task_gap_detector = GapDetector()
        
        # Create appropriate adapter
        if exchange_type == "BINANCE":
            adapter = BinanceAdapter(api_key="", api_secret="", testnet=False)
        else:
            logger.error(f"Unsupported exchange type: {exchange_type}")
            return
        
        task_market_data_service = MarketDataService(
            exchange_adapter=adapter,
            candle_repository=task_candle_repo,
            metadata_repository=task_metadata_repo,
            gap_detector=task_gap_detector
        )
        
        task_use_case = RunBacktestUseCase(task_repo, task_market_data_service)
        
        # Load strategy function
        from ...strategies.backtest_adapter import get_strategy_function
        strategy_func = get_strategy_function(
            strategy_id=str(strategy_id),
            strategy_name=strategy_name,
            config=config_dict,
            code_content=strategy_code
        )
        
        # Reconstruct config from dict
        config = BacktestConfig(**config_dict)
        
        try:
            result = await task_use_case.execute(
                user_id=user_id,
                strategy_id=strategy_id,
                config=config,
                symbol=symbol,
                timeframe=timeframe,
                start_date=start_date,
                end_date=end_date,
                strategy_func=strategy_func,
                backtest_run_id=backtest_id,
            )
            logger.info(f"Executor task completed for backtest {backtest_id}")
        except Exception as e:
            logger.error(f"Backtest task failed: {str(e)}")
            import traceback
            traceback.print_exc()



@router.get("/available-exchanges")
async def get_available_exchanges(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get list of available exchanges for the user (for backtest selection)."""
    repo = ExchangeRepository(db)
    exchanges = await repo.get_available_exchanges(current_user.id)
    return exchanges


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
        exchange_repo = ExchangeRepository(repository._session)
        
        # Determine connection and exchange settings
        exchange_connection = None
        adapter = None
        
        if request.exchange_name:
            # New Flow: User selected an Exchange (e.g. BINANCE)
            try:
                # Find ANY connection for this user and exchange type to satisfy DB FK
                exchange_name_upper = request.exchange_name.upper()
                connections = await exchange_repo.find_by_user_and_exchange(
                    user_id, 
                    ExchangeType(exchange_name_upper)
                )
                
                if not connections:
                     raise HTTPException(
                        status_code=400,
                        detail=f"No connection found for exchange {exchange_name_upper}. Please connect an account first."
                    )
                
                # Use the first available connection for ID reference
                exchange_connection = connections[0]
                
                # Force Mainnet Adapter (with empty keys for public data)
                if exchange_connection.exchange_type == ExchangeType.BINANCE:
                    adapter = BinanceAdapter(api_key="", api_secret="", testnet=False)
                else:
                    raise HTTPException(400, f"Exchange {exchange_name_upper} not supported for backtesting yet")
                    
            except ValueError:
                 raise HTTPException(400, f"Invalid exchange name: {request.exchange_name}")
                 
        elif request.exchange_connection_id:
            # Legacy Flow: User provided specific connection ID
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
                
            # Force Mainnet Adapter here too (fix for bug where Testnet connection used Testnet data)
            if exchange_connection.exchange_type == ExchangeType.BINANCE:
                # Always use Mainnet data for backtesting, even if connection is Testnet
                adapter = BinanceAdapter(api_key="", api_secret="", testnet=False)
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Exchange type {exchange_connection.exchange_type} not yet supported for backtesting"
                )
        else:
            raise HTTPException(
                status_code=400,
                detail="Either exchange_name or exchange_connection_id must be provided"
            )
        
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
            commission_percent=request.config.commission_rate / 100,  # Legacy
            leverage=request.config.leverage,
            taker_fee_rate=request.config.taker_fee_rate / 100,
            maker_fee_rate=request.config.maker_fee_rate / 100,
            funding_rate_daily=request.config.funding_rate_daily / 100,
            
            # Phase 1-3 New Fields
            fill_policy=request.config.fill_policy,
            market_fill_policy=request.config.market_fill_policy,
            limit_fill_policy=request.config.limit_fill_policy,
            price_path_assumption=request.config.price_path_assumption,
            signal_timeframe=request.config.signal_timeframe,
            execution_delay_bars=request.config.execution_delay_bars,
            enable_setup_trigger_model=request.config.enable_setup_trigger_model,
            setup_validity_window_minutes=request.config.setup_validity_window_minutes,
            
            # Phase 2: Condition Timeframes
            condition_timeframes=request.config.condition_timeframes,
        )
        logger.info(f"DEBUG CONTROLLER: Created Config - Leverage: {config.leverage}, Taker: {config.taker_fee_rate}, Maker: {config.maker_fee_rate}")
        logger.info(f"DEBUG CONTROLLER: Policies - Market: {config.market_fill_policy}, Limit: {config.limit_fill_policy}, Assumption: {config.price_path_assumption}")
        
        # Fetch Strategy Name from DB
        from ...infrastructure.persistence.models.bot_models import StrategyModel
        from sqlalchemy import select
        
        stmt = select(StrategyModel).where(StrategyModel.id == request.strategy_id)
        result = await repository._session.execute(stmt)
        strategy_entity = result.scalars().first()
        
        # If strategy not found, it might fail FK constraint later, but for now default to Unknown
        strategy_name_db = strategy_entity.name if strategy_entity else None
        
        # Load strategy function dynamically based on strategy_id
        from ...strategies.backtest_adapter import get_strategy_function
        
        # Get strategy parameters from config if available
        strategy_config = getattr(request.config, 'strategy_params', None) or {}
        
        # Check if we have a type from DB
        strategy_type = strategy_entity.strategy_type if strategy_entity else None
        strategy_code = strategy_entity.code_content if strategy_entity else None
        
        # Use strategy name from DB directly (No magic mapping)
        strategy_implementation_name = strategy_name_db

        logger.info(f"Loading strategy for backtest. ID: {request.strategy_id}, Name: {strategy_name_db}, Has Code: {bool(strategy_code)}")

        strategy_func = get_strategy_function(
            strategy_id=str(request.strategy_id),
            strategy_name=strategy_implementation_name,
            config={**strategy_config, "leverage": config.leverage},
            code_content=strategy_code
        )
        
        logger.info(f"Loaded strategy function for ID: {request.strategy_id}")
        

        # Create backtest run entity FIRST (before background task)
        backtest_id = uuid.uuid4()
        backtest_run = BacktestRun(
            id=backtest_id,
            user_id=current_user.id,
            strategy_id=request.strategy_id,
            exchange_connection_id=exchange_connection.id,
            exchange_name=exchange_connection.name, 
            symbol=request.config.symbol,
            timeframe=request.config.timeframe,
            start_date=request.config.start_date,
            end_date=request.config.end_date,
            config=config,
        )

        await repository.save(backtest_run)
        
        # Run backtest asynchronously using create_task
        # This is decoupled from the request lifecycle and runs in the background
        # The run_backtest_in_executor function handles its own DB session
        from dataclasses import asdict
        config_dict = asdict(config)
        
        asyncio.create_task(
            run_backtest_in_executor(
                backtest_id=backtest_id,
                user_id=user_id,
                strategy_id=request.strategy_id,
                config_dict=config_dict,
                symbol=request.config.symbol,
                timeframe=request.config.timeframe,
                start_date=request.config.start_date,
                end_date=request.config.end_date,
                strategy_name=strategy_name_db,
                strategy_code=strategy_code,
                exchange_type=str(exchange_connection.exchange_type.value),
                is_testnet=exchange_connection.is_testnet,
            )
        )
        
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
        
        # Verify exit reason data
        pass

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
                    "pnl_percent": float(trade.pnl_percent) if trade.pnl_percent is not None else None,
                    "pnl_pct": float(trade.pnl_percent) if trade.pnl_percent is not None else None, # Legacy support
                    "mae": float(trade.mae) if trade.mae is not None else None,
                    "mfe": float(trade.mfe) if trade.mfe is not None else None,
                    "maker_fee": float(trade.maker_fee) if getattr(trade, "maker_fee", None) is not None else 0.0,
                    "taker_fee": float(trade.taker_fee) if getattr(trade, "taker_fee", None) is not None else 0.0,
                    "funding_fee": float(trade.funding_fee) if getattr(trade, "funding_fee", None) is not None else 0.0,
                    "duration": trade.duration_seconds if hasattr(trade, 'duration_seconds') else None,
                    "entry_time": trade.entry_time.isoformat() if trade.entry_time else None,
                    "exit_time": trade.exit_time.isoformat() if trade.exit_time else None,
                    "entry_reason": trade.entry_reason,
                    "exit_reason": trade.exit_reason,
                    "initial_entry_price": float(trade.initial_entry_price) if getattr(trade, "initial_entry_price", None) is not None else None,
                    "initial_entry_quantity": float(trade.initial_entry_quantity) if getattr(trade, "initial_entry_quantity", None) is not None else None,
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
                "Quantity", "MAE%", "MFE%", "P&L", "P&L%", "Duration (mins)", "Entry Time", "Exit Time"
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
                        trade.entry_time.isoformat(),
                        trade.symbol,
                        trade.direction.value,
                        float(trade.entry_price),
                        float(trade.exit_price) if trade.exit_price else "",
                        float(trade.quantity),
                        float(trade.mae) if trade.mae is not None else 0.0,
                        float(trade.mfe) if trade.mfe is not None else 0.0,
                        float(trade.net_pnl) if trade.net_pnl is not None else 0.0,
                        float(trade.pnl_percent) if trade.pnl_percent is not None else 0.0,
                        trade.duration_seconds // 60 if hasattr(trade, 'duration_seconds') and trade.duration_seconds else 0,
                        trade.entry_time.isoformat(),
                        trade.exit_time.isoformat() if trade.exit_time else ""
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


@router.get("/{backtest_id}/events")
async def get_backtest_events(
    backtest_id: UUID,
    trade_id: Optional[UUID] = Query(None, description="Filter by trade ID"),
    event_types: Optional[List[str]] = Query(None, description="Filter by event types"),
    user_id: UUID = Depends(get_current_user_id),
    repository: BacktestRepository = Depends(get_backtest_repository),
):
    """
    Get significant events that occurred during a backtest.
    
    Returns a sequence of events (entry, exits, updates, scale-ins) for 
    the whole backtest or a specific trade.
    """
    
    # Verify backtest exists and ownership
    use_case = GetBacktestUseCase(repository)
    backtest_run = await use_case.execute(backtest_id)
    
    if not backtest_run:
        raise HTTPException(status_code=404, detail="Backtest not found")
    
    if backtest_run.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    try:
        events = await repository.get_backtest_events(
            backtest_id=backtest_id,
            trade_id=trade_id,
            event_types=event_types
        )
        
        return [
            {
                "id": str(e.id),
                "timestamp": e.timestamp.isoformat(),
                "event_type": e.event_type,
                "details": e.details,
                "trade_id": str(e.trade_id) if e.trade_id else None
            }
            for e in events
        ]
        
    except Exception as e:
        logger.error(f"Failed to get backtest events: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{backtest_id}/period-stats", response_model=BacktestPeriodStatsResponse)
async def get_backtest_period_stats(
    backtest_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    repository: BacktestRepository = Depends(get_backtest_repository),
):
    """
    Get period-based statistics for backtest.
    
    Returns profit and trade statistics grouped by day/week/month/year.
    """
    
    # Verify backtest exists and ownership
    use_case = GetBacktestUseCase(repository)
    backtest_run = await use_case.execute(backtest_id)
    
    if not backtest_run:
        raise HTTPException(status_code=404, detail="Backtest not found")
    
    if backtest_run.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    try:
        # Get all trades for this backtest
        trades = await repository.get_backtest_trades(
            backtest_id=backtest_id,
            page=1,
            limit=100000  # Get all trades
        )
        
        if not trades:
            # Return zeros if no trades
            empty_profit = PeriodProfitStats(avg_profit=0.0, max_profit=0.0, min_profit=0.0)
            empty_trades = PeriodTradeStats(avg_trades=0.0, max_trades=0, min_trades=0)
            return BacktestPeriodStatsResponse(
                profit_day=empty_profit, profit_week=empty_profit,
                profit_month=empty_profit, profit_year=empty_profit,
                trades_day=empty_trades, trades_week=empty_trades,
                trades_month=empty_trades, trades_year=empty_trades,
            )
        
        from collections import defaultdict
        
        def get_iso_week(dt):
            """Get ISO week number."""
            return dt.isocalendar()[1]
        
        def get_period_key(entry_time, period: str) -> str:
            """Get period key from datetime."""
            if period == 'day':
                return entry_time.strftime('%Y-%m-%d')
            elif period == 'week':
                return f"{entry_time.year}-W{get_iso_week(entry_time):02d}"
            elif period == 'month':
                return entry_time.strftime('%Y-%m')
            elif period == 'year':
                return str(entry_time.year)
            return ''
        
        def calculate_period_stats(trades_list, period: str):
            """Calculate stats for a period type."""
            period_data = defaultdict(lambda: {'profit': 0.0, 'trades': 0})
            
            for trade in trades_list:
                if trade.entry_time:
                    key = get_period_key(trade.entry_time, period)
                    pnl = float(trade.net_pnl) if trade.net_pnl else 0.0
                    period_data[key]['profit'] += pnl
                    period_data[key]['trades'] += 1
            
            if not period_data:
                return (
                    PeriodProfitStats(avg_profit=0.0, max_profit=0.0, min_profit=0.0),
                    PeriodTradeStats(avg_trades=0.0, max_trades=0, min_trades=0)
                )
            
            profits = [v['profit'] for v in period_data.values()]
            trade_counts = [v['trades'] for v in period_data.values()]
            
            profit_stats = PeriodProfitStats(
                avg_profit=sum(profits) / len(profits),
                max_profit=max(profits),
                min_profit=min(profits),
            )
            
            trade_stats = PeriodTradeStats(
                avg_trades=sum(trade_counts) / len(trade_counts),
                max_trades=max(trade_counts),
                min_trades=min(trade_counts),
            )
            
            return profit_stats, trade_stats
        
        # Calculate for each period type
        day_profit, day_trades = calculate_period_stats(trades, 'day')
        week_profit, week_trades = calculate_period_stats(trades, 'week')
        month_profit, month_trades = calculate_period_stats(trades, 'month')
        year_profit, year_trades = calculate_period_stats(trades, 'year')
        
        return BacktestPeriodStatsResponse(
            profit_day=day_profit,
            profit_week=week_profit,
            profit_month=month_profit,
            profit_year=year_profit,
            trades_day=day_trades,
            trades_week=week_trades,
            trades_month=month_trades,
            trades_year=year_trades,
        )
        
    except Exception as e:
        logger.error(f"Failed to get period stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

