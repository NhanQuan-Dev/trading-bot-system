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
        strategy_func,  # Strategy function that generates signals
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
        
        # Create backtest run
        backtest_run = BacktestRun(
            user_id=user_id,
            strategy_id=strategy_id,
            config=config,
        )
        
        # Save initial state
        await self.repository.save(backtest_run)
        
        try:
            # Fetch historical data
            logger.info(f"Fetching historical data for {config.symbol} from {config.start_date} to {config.end_date}")
            candles = await self.market_data_service.get_historical_candles(
                symbol=config.symbol,
                timeframe=config.timeframe,
                start_date=config.start_date,
                end_date=config.end_date,
            )
            
            if not candles:
                raise ValueError("No historical data available for specified period")
            
            # Create engine
            engine = BacktestEngine(
                config=config,
                metrics_calculator=MetricsCalculator(),
                market_simulator=MarketSimulator(
                    slippage_model=config.slippage_model,
                    slippage_percent=config.slippage_percent,
                    commission_model=config.commission_model,
                    commission_rate=config.commission_rate,
                ),
            )
            
            # Progress callback
            async def progress_callback(percent: int):
                backtest_run.update_progress(percent)
                await self.repository.save(backtest_run)
            
            # Run backtest
            results = await engine.run_backtest(
                candles=candles,
                strategy_func=strategy_func,
                backtest_run=backtest_run,
                progress_callback=progress_callback,
            )
            
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
        results = await self.results_service.get_results(backtest_id)
        
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
        Delete backtest.
        
        Args:
            backtest_id: Backtest to delete
            user_id: User requesting deletion
            
        Returns:
            True if deleted successfully
        """
        
        backtest_run = await self.repository.get_by_id(backtest_id)
        
        if not backtest_run:
            return False
        
        # Verify ownership
        if backtest_run.user_id != user_id:
            raise PermissionError("Not authorized to delete this backtest")
        
        # Don't delete running backtests
        if backtest_run.status == BacktestStatus.RUNNING:
            raise ValueError("Cannot delete running backtest, cancel it first")
        
        return await self.repository.delete(backtest_id)
