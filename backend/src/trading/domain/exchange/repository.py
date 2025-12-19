"""Exchange repository interface."""
from abc import ABC, abstractmethod
from typing import Optional, List
import uuid

from . import ExchangeConnection, ExchangeType


class IExchangeRepository(ABC):
    """Repository interface for exchange connections."""
    
    @abstractmethod
    async def save(self, connection: ExchangeConnection) -> None:
        """Save or update exchange connection."""
        pass
    
    @abstractmethod
    async def find_by_id(self, connection_id: uuid.UUID) -> Optional[ExchangeConnection]:
        """Find connection by ID."""
        pass
    
    @abstractmethod
    async def find_by_user(self, user_id: uuid.UUID) -> List[ExchangeConnection]:
        """Find all connections for a user."""
        pass
    
    @abstractmethod
    async def find_by_user_and_exchange(
        self, 
        user_id: uuid.UUID, 
        exchange_type: ExchangeType
    ) -> List[ExchangeConnection]:
        """Find user's connections for specific exchange."""
        pass
    
    @abstractmethod
    async def find_active_by_user(self, user_id: uuid.UUID) -> List[ExchangeConnection]:
        """Find active connections for a user."""
        pass
    
    @abstractmethod
    async def delete(self, connection_id: uuid.UUID) -> None:
        """Delete (soft delete) connection."""
        pass
