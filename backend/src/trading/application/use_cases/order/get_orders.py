"""Get orders use case."""
from typing import List, Optional, Dict, Any
from datetime import datetime as dt
import uuid

from ....domain.order import Order, OrderStatus, OrderSide
from ....interfaces.repositories.order_repository import IOrderRepository


class GetOrdersUseCase:
    """Use case for retrieving orders."""
    
    def __init__(self, order_repository: IOrderRepository):
        self._order_repository = order_repository
    
    async def execute(
        self,
        user_id: uuid.UUID,
        symbol: Optional[str] = None,
        status: Optional[OrderStatus] = None,
        side: Optional[OrderSide] = None,
        exchange_connection_id: Optional[uuid.UUID] = None,
        bot_id: Optional[uuid.UUID] = None,
        start_time: Optional[dt] = None,
        end_time: Optional[dt] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Execute get orders use case."""
        
        # Build filters
        filters = {"user_id": user_id}
        
        if symbol:
            filters["symbol"] = symbol
        if status:
            filters["status"] = status
        if side:
            filters["side"] = side
        if exchange_connection_id:
            filters["exchange_connection_id"] = exchange_connection_id
        if bot_id:
            filters["bot_id"] = bot_id
        if start_time:
            filters["start_time"] = start_time
        if end_time:
            filters["end_time"] = end_time
        
        # Get orders and total count
        orders = await self._order_repository.find_by_filters(
            filters=filters,
            limit=limit,
            offset=offset,
            order_by="created_at",
            desc=True
        )
        
        total_count = await self._order_repository.count_by_filters(filters)
        
        return {
            "orders": orders,
            "total_count": total_count,
            "limit": limit,
            "offset": offset,
            "has_more": (offset + len(orders)) < total_count
        }
