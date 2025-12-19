"""Order repository interface."""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime as dt
import uuid

from ...domain.order import Order, OrderStatus, OrderSide


class IOrderRepository(ABC):
    """Interface for order repository."""
    
    @abstractmethod
    async def create(self, order: Order) -> Order:
        """Create a new order."""
        pass
    
    @abstractmethod
    async def get_by_id(self, order_id: uuid.UUID, user_id: uuid.UUID) -> Optional[Order]:
        """Get order by ID and user ID."""
        pass
    
    @abstractmethod
    async def get_by_exchange_order_id(
        self, 
        exchange_order_id: str, 
        user_id: uuid.UUID
    ) -> Optional[Order]:
        """Get order by exchange order ID."""
        pass
    
    @abstractmethod
    async def get_by_client_order_id(
        self,
        client_order_id: str,
        user_id: uuid.UUID
    ) -> Optional[Order]:
        """Get order by client order ID."""
        pass
    
    @abstractmethod
    async def list_by_user(
        self, 
        user_id: uuid.UUID,
        status: Optional[OrderStatus] = None,
        symbol: Optional[str] = None,
        bot_id: Optional[uuid.UUID] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Order]:
        """List orders by user with filters."""
        pass
    
    @abstractmethod
    async def list_active_by_user(self, user_id: uuid.UUID) -> List[Order]:
        """List active orders by user."""
        pass
    
    @abstractmethod
    async def list_by_bot(self, bot_id: uuid.UUID) -> List[Order]:
        """List orders by bot."""
        pass
    
    @abstractmethod
    async def update(self, order: Order) -> Order:
        """Update an existing order."""
        pass
    
    @abstractmethod
    async def update_status(
        self, 
        order_id: uuid.UUID, 
        user_id: uuid.UUID, 
        status: OrderStatus,
        error_message: Optional[str] = None
    ) -> Optional[Order]:
        """Update order status."""
        pass
    
    @abstractmethod
    async def update_execution(
        self,
        order_id: uuid.UUID,
        user_id: uuid.UUID,
        executed_quantity: float,
        executed_price: float,
        commission: float = 0.0,
        commission_asset: str = "USDT"
    ) -> Optional[Order]:
        """Update order execution details."""
        pass
    
    @abstractmethod
    async def cancel_order(
        self, 
        order_id: uuid.UUID, 
        user_id: uuid.UUID,
        reason: Optional[str] = None
    ) -> Optional[Order]:
        """Cancel an order."""
        pass
    
    @abstractmethod
    async def cancel_all_by_symbol(
        self,
        user_id: uuid.UUID,
        symbol: str
    ) -> List[Order]:
        """Cancel all active orders for a symbol."""
        pass
    
    @abstractmethod
    async def cancel_all_by_bot(self, bot_id: uuid.UUID) -> List[Order]:
        """Cancel all active orders for a bot."""
        pass
    
    @abstractmethod
    async def get_order_count(self, user_id: uuid.UUID, status: Optional[OrderStatus] = None) -> int:
        """Get order count for user."""
        pass
    
    @abstractmethod
    async def get_volume_stats(
        self,
        user_id: uuid.UUID,
        symbol: Optional[str] = None,
        start_date: Optional[dt] = None,
        end_date: Optional[dt] = None
    ) -> Dict[str, Any]:
        """Get volume statistics for user."""
        pass
    
    @abstractmethod
    async def find_by_filters(
        self,
        filters: Dict[str, Any],
        limit: int = 100,
        offset: int = 0,
        order_by: str = "created_at",
        desc: bool = True
    ) -> List[Order]:
        """Find orders by filters."""
        pass
    
    @abstractmethod
    async def count_by_filters(self, filters: Dict[str, Any]) -> int:
        """Count orders by filters."""
        pass