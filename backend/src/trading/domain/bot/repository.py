"""Bot and Strategy repository interfaces."""
from abc import ABC, abstractmethod
from typing import List, Optional
import uuid

from ..bot import Bot, Strategy, BotStatus, StrategyType


class IBotRepository(ABC):
    """Repository interface for Bot aggregate."""
    
    @abstractmethod
    async def save(self, bot: Bot) -> Bot:
        """Save or update bot."""
        pass
    
    @abstractmethod
    async def find_by_id(self, bot_id: uuid.UUID) -> Optional[Bot]:
        """Find bot by ID."""
        pass
    
    @abstractmethod
    async def find_by_user(self, user_id: uuid.UUID) -> List[Bot]:
        """Find all bots for a user."""
        pass
    
    @abstractmethod
    async def find_by_user_and_status(self, user_id: uuid.UUID, status: BotStatus) -> List[Bot]:
        """Find bots by status for a user."""
        pass
    
    @abstractmethod
    async def find_by_strategy_id(self, strategy_id: uuid.UUID) -> List[Bot]:
        """Find bots using specific strategy."""
        pass
    
    @abstractmethod
    async def find_active_bots(self) -> List[Bot]:
        """Find all active bots across all users."""
        pass
    
    @abstractmethod
    async def exists_by_name_and_user(self, name: str, user_id: uuid.UUID) -> bool:
        """Check if bot with name exists for user."""
        pass
    
    @abstractmethod
    async def delete(self, bot_id: uuid.UUID) -> None:
        """Delete bot (soft delete)."""
        pass


class IStrategyRepository(ABC):
    """Repository interface for Strategy aggregate."""
    
    @abstractmethod
    async def save(self, strategy: Strategy) -> Strategy:
        """Save or update strategy."""
        pass
    
    @abstractmethod
    async def find_by_id(self, strategy_id: uuid.UUID) -> Optional[Strategy]:
        """Find strategy by ID."""
        pass
    
    @abstractmethod
    async def find_by_user(self, user_id: uuid.UUID) -> List[Strategy]:
        """Find all strategies for a user."""
        pass
    
    @abstractmethod
    async def find_by_type(self, strategy_type: StrategyType) -> List[Strategy]:
        """Find strategies by type."""
        pass
    
    @abstractmethod
    async def find_active_strategies(self) -> List[Strategy]:
        """Find all active strategies."""
        pass
    
    @abstractmethod
    async def exists_by_name_and_user(self, name: str, user_id: uuid.UUID) -> bool:
        """Check if strategy with name exists for user."""
        pass
    
    @abstractmethod
    async def delete(self, strategy_id: uuid.UUID) -> None:
        """Delete strategy (soft delete)."""
        pass


__all__ = ["IBotRepository", "IStrategyRepository"]
