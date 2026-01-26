"""Backtesting use cases."""

import logging
from typing import List, Optional, Dict
from uuid import UUID
from datetime import datetime

from ...domain.backtesting import (
    BacktestRun,
    BacktestResults,
    BacktestConfig,
    BacktestStatus,
    IBacktestRepository,
)
from ...infrastructure.backtesting import (
    BacktestEngine,
    MetricsCalculator,
    MarketSimulator,
)

logger = logging.getLogger(__name__)


class RunBacktestUseCase:
    """Execute a backtest run."""
    
    def __init__(
        self,
        repository: IBacktestRepository,
        market_data_service,  # Service to fetch historical candles
    ):
        """Initialize use case."""
        self.repository = repository
        self.market_data_service = market_data_service
    
    async def execute(
        self,
        user_id: UUID,
        strategy_id: UUID,

        config: BacktestConfig,
        symbol: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime,
        strategy_func,  # Strategy function that generates signals
        backtest_run_id: UUID = None,  # Optional: use existing run to prevent duplicate
    ) -> BacktestRun:
        """
        Run backtest.
        
        Args:
            user_id: User running the backtest
            strategy_id: Strategy to test
            config: Backtest configuration
            strategy_func: Strategy function for signal generation
            
        Returns:
            BacktestRun entity with execution tracking
        """
        
        # Load existing or create new backtest run
        if backtest_run_id:
            # Load existing backtest run
            backtest_run = await self.repository.get_by_id(backtest_run_id)
            if not backtest_run:
                raise ValueError(f"Backtest run {backtest_run_id} not found")
        else:
            # Create new backtest run
            backtest_run = BacktestRun(
                user_id=user_id,
                strategy_id=strategy_id,
                config=config,
                symbol=symbol,
                timeframe=timeframe,
                start_date=start_date,
                end_date=end_date,
            )
            # Save initial state
            await self.repository.save(backtest_run)
        
        try:
            # Fetch historical data - now with wait_for_data=True
            # MarketDataService will queue repair job AND poll DB until data is available
            logger.info(f"Fetching historical data for {symbol} from {start_date} to {end_date}")
            
            # Start the backtest NOW to show RUNNING status in UI
            backtest_run.start()
            await self.repository.save(backtest_run)
            
            # Define progress callback to update backtest progress during data fetch
            # Maps data fetch progress (0-100%) to first 80% of total backtest (User requested 80% for fetching)
            async def data_fetch_progress_callback(percent: int, message: str):
                """Update backtest progress during data fetching phase."""
                overall_percent = int(percent * 0.8)
                backtest_run.update_progress(overall_percent, message)  # Pass message to show on UI
                logger.info(f"Data fetch progress: {percent}% (Overall: {overall_percent}%) - {message}")
                await self.repository.save(backtest_run)
            
            candles = await self.market_data_service.get_historical_candles(
                symbol=symbol,
                timeframe=timeframe,
                start_date=start_date,
                end_date=end_date,
                limit=None,  # CRITICAL: No limit for backtests - fetch ALL candles in date range
                repair=True,  # Auto-repair missing data
                wait_for_data=True,  # NEW: Wait for data to be fetched before returning
                max_wait_seconds=600,  # 10 minutes max wait
                poll_interval_seconds=5,  # Check every 5 seconds
                progress_callback=data_fetch_progress_callback,  # Pass progress callback
            )
            
            if not candles or len(candles) == 0:
                raise ValueError(
                    f"No historical data available for {symbol} {timeframe} "
                    f"from {start_date} to {end_date}. "
                    "Please check if the requested time range has data available on the exchange."
                )
            
            logger.info(f"Fetched {len(candles)} candles for backtest")
            
            # Create engine
            engine = BacktestEngine(
                config=config,
                metrics_calculator=MetricsCalculator(),
                market_simulator=MarketSimulator(
                    slippage_model=config.slippage_model,
                    slippage_percent=config.slippage_percent,
                    commission_model=config.commission_model,
                    commission_rate=config.commission_percent,  # MarketSimulator expects commission_rate param
                    market_fill_policy=config.market_fill_policy,
                    limit_fill_policy=config.limit_fill_policy,
                ),
            )
            
            # Progress callback for backtest engine (scales 0-100% to 80-100% overall)
            # Progress callback for backtest engine (scales 0-100% to 80-100% overall)
            # Fetching is 80%, Simulation is 20% (per user request)
            last_save_time = 0
            
            async def progress_callback(percent: int):
                nonlocal last_save_time
                # Scale engine progress (0-100%) to overall progress (80-100%)
                overall_percent = 80 + int(percent * 0.2)
                message = f"Process {percent}% candles..."
                backtest_run.update_progress(overall_percent, message)
                
                # OPTIMIZATION: Debounce DB saves to max once every 2 seconds
                # This prevents "15 transactions/sec" spam which locks the DB and slows down the UI
                current_time = datetime.utcnow().timestamp()
                if current_time - last_save_time > 2.0 or percent == 100 or percent % 10 == 0:
                    await self.repository.save(backtest_run)
                    last_save_time = current_time
            
            # Run backtest
            logger.info(f"Running backtest engine with {len(candles)} candles...")
            results = await engine.run_backtest(
                candles=candles,
                strategy_func=strategy_func,
                backtest_run=backtest_run,
                progress_callback=progress_callback,
            )
            logger.info("Backtest engine completed")
            
            # Save final state
            await self.repository.save(backtest_run)
            
            logger.info(f"Backtest completed: {backtest_run.id}")
            return backtest_run
            
        except Exception as e:
            logger.error(f"Backtest failed: {str(e)}")
            backtest_run.fail(str(e))
            await self.repository.save(backtest_run)
            raise


class GetBacktestUseCase:
    """Get backtest run by ID."""
    
    def __init__(self, repository: IBacktestRepository):
        """Initialize use case."""
        self.repository = repository
    
    async def execute(self, backtest_id: UUID) -> Optional[BacktestRun]:
        """Get backtest run."""
        return await self.repository.get_by_id(backtest_id)


class ListBacktestsUseCase:
    """List backtests with filters."""
    
    def __init__(self, repository: IBacktestRepository):
        """Initialize use case."""
        self.repository = repository
    
    async def execute(
        self,
        user_id: Optional[UUID] = None,
        strategy_id: Optional[UUID] = None,
        symbol: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[BacktestRun]:
        """
        List backtests with filters.
        
        Args:
            user_id: Filter by user
            strategy_id: Filter by strategy
            symbol: Filter by symbol
            limit: Maximum results
            offset: Pagination offset
            
        Returns:
            List of backtest runs
        """
        
        if strategy_id:
            return await self.repository.get_by_strategy(strategy_id, limit)
        elif symbol:
            return await self.repository.get_by_symbol(symbol, limit)
        elif user_id:
            return await self.repository.get_by_user(user_id, limit, offset)
        else:
            # Return running backtests by default
            return await self.repository.get_running_backtests()


class GetBacktestResultsUseCase:
    """Get detailed backtest results."""
    
    def __init__(
        self,
        repository: IBacktestRepository,
        results_service,  # Service to fetch detailed results
    ):
        """Initialize use case."""
        self.repository = repository
        self.results_service = results_service
    
    async def execute(self, backtest_id: UUID) -> Optional[Dict]:
        """
        Get backtest results with full details.
        
        Returns:
            Dictionary with:
            - backtest_run: BacktestRun entity
            - results: BacktestResults with metrics
            - equity_curve: Equity curve data
            - trades: Trade list
        """
        
        backtest_run = await self.repository.get_by_id(backtest_id)
        
        if not backtest_run:
            return None
        
        if backtest_run.status != BacktestStatus.COMPLETED:
            return {
                "backtest_run": backtest_run,
                "results": None,
                "message": f"Backtest is {backtest_run.status}, results not available"
            }
        
        # Fetch detailed results
        results = await self.repository.get_results(backtest_id)
        
        if results:
            results["backtest_run"] = backtest_run
        
        return {
            "backtest_run": backtest_run,
            "results": results,
        }


class CancelBacktestUseCase:
    """Cancel running backtest."""
    
    def __init__(self, repository: IBacktestRepository):
        """Initialize use case."""
        self.repository = repository
    
    async def execute(self, backtest_id: UUID, user_id: UUID) -> bool:
        """
        Cancel backtest.
        
        Args:
            backtest_id: Backtest to cancel
            user_id: User requesting cancellation
            
        Returns:
            True if cancelled successfully
        """
        
        backtest_run = await self.repository.get_by_id(backtest_id)
        
        if not backtest_run:
            return False
        
        # Verify ownership
        if backtest_run.user_id != user_id:
            raise PermissionError("Not authorized to cancel this backtest")
        
        # Only cancel if running
        if backtest_run.status not in [BacktestStatus.PENDING, BacktestStatus.RUNNING]:
            return False
        
        backtest_run.cancel()
        await self.repository.save(backtest_run)
        
        logger.info(f"Backtest cancelled: {backtest_id}")
        return True


class DeleteBacktestUseCase:
    """Delete backtest run."""
    
    def __init__(self, repository: IBacktestRepository):
        """Initialize use case."""
        self.repository = repository
    
    async def execute(self, backtest_id: UUID, user_id: UUID) -> bool:
        """
        Delete backtest and cancel any related jobs.
        
        Args:
            backtest_id: Backtest to delete
            user_id: User requesting deletion
            
        Returns:
            True if deleted successfully
        """
        from ...infrastructure.jobs.job_queue import job_queue
        
        backtest_run = await self.repository.get_by_id(backtest_id)
        
        if not backtest_run:
            return False
        
        # Verify ownership
        if backtest_run.user_id != user_id:
            raise PermissionError("Not authorized to delete this backtest")
        
        # Cancel any pending jobs for this backtest BEFORE deleting
        # This prevents orphaned jobs from continuing to run
        try:
            cancelled_count = await job_queue.cancel_jobs_by_backtest_id(str(backtest_id))
            if cancelled_count > 0:
                logger.info(f"Cancelled {cancelled_count} jobs before deleting backtest {backtest_id}")
        except Exception as e:
            logger.warning(f"Failed to cancel jobs for backtest {backtest_id}: {e}")
            # Continue with delete even if job cancellation fails
        
        return await self.repository.delete(backtest_id)

