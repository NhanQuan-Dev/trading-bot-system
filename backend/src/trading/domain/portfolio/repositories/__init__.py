"""Portfolio Repository Interface."""
from abc import ABC, abstractmethod
from typing import Optional, List
import uuid

from ..aggregates import Portfolio
from ..entities import Position


class IPortfolioRepository(ABC):
    """Portfolio repository interface."""
    
    @abstractmethod
    async def save(self, portfolio: Portfolio) -> None:
        """Save portfolio aggregate."""
        pass
    
    @abstractmethod
    async def find_by_user_id(self, user_id: uuid.UUID) -> Optional[Portfolio]:
        """Find portfolio by user ID."""
        pass
    
    @abstractmethod
    async def find_position(self, position_id: uuid.UUID) -> Optional[Position]:
        """Find position by ID."""
        pass
    
    @abstractmethod
    async def find_positions_by_user(self, user_id: uuid.UUID) -> List[Position]:
        """Find all positions for a user."""
        pass
    
    @abstractmethod
    async def find_open_positions(self, user_id: uuid.UUID) -> List[Position]:
        """Find all open positions for a user."""
        pass
    
    @abstractmethod
    async def delete_position(self, position_id: uuid.UUID) -> None:
        """Delete position (soft delete)."""
        pass
