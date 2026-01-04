"""Trade repository interface."""
from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from ...domain.trade import Trade

class ITradeRepository(ABC):
    """Interface for trade repository."""
    
    @abstractmethod
    async def create(self, trade: Trade) -> Trade:
        """Create a new trade."""
        pass
        
    @abstractmethod
    async def get_by_bot_id(self, bot_id: UUID) -> List[Trade]:
        """Get all trades for a bot."""
        pass
        
    @abstractmethod
    async def get_by_order_id(self, order_id: UUID) -> List[Trade]:
        """Get all trades for an order."""
        pass
