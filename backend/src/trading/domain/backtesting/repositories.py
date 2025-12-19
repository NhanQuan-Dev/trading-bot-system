"""Backtesting repository interface."""

from abc import ABC, abstractmethod
from typing import Optional, List
from uuid import UUID
from datetime import datetime

from .entities import BacktestRun, BacktestResults


class IBacktestRepository(ABC):
    """Repository interface for backtesting operations."""
    
    @abstractmethod
    async def save(self, backtest: BacktestRun) -> BacktestRun:
        """Save or update a backtest run."""
        pass
    
    @abstractmethod
    async def get_by_id(self, backtest_id: UUID) -> Optional[BacktestRun]:
        """Get backtest by ID."""
        pass
    
    @abstractmethod
    async def get_by_user(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[BacktestRun]:
        """Get all backtests for a user."""
        pass
    
    @abstractmethod
    async def get_by_strategy(
        self,
        strategy_id: UUID,
        skip: int = 0,
        limit: int = 50
    ) -> List[BacktestRun]:
        """Get backtests for a specific strategy."""
        pass
    
    @abstractmethod
    async def get_by_symbol(
        self,
        user_id: UUID,
        symbol: str,
        skip: int = 0,
        limit: int = 50
    ) -> List[BacktestRun]:
        """Get backtests for a specific symbol."""
        pass
    
    @abstractmethod
    async def delete(self, backtest_id: UUID) -> bool:
        """Delete a backtest run."""
        pass
    
    @abstractmethod
    async def count_by_user(self, user_id: UUID) -> int:
        """Count total backtests for a user."""
        pass
    
    @abstractmethod
    async def get_running_backtests(self) -> List[BacktestRun]:
        """Get all currently running backtests."""
        pass
