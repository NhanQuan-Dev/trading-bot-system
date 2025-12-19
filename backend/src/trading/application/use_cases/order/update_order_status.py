"""Update order status use case."""
import uuid
import logging
from decimal import Decimal
from typing import Optional
from datetime import datetime as dt, timezone as dt_timezone

from ....domain.order import Order, OrderStatus
from ....interfaces.repositories.order_repository import IOrderRepository
from ....shared.exceptions.business import NotFoundError, ValidationError

logger = logging.getLogger(__name__)


class UpdateOrderStatusUseCase:
    """Use case for updating order status (typically from exchange events)."""
    
    def __init__(self, order_repository: IOrderRepository):
        self._order_repository = order_repository
    
    async def execute(
        self,
        user_id: uuid.UUID,
        order_id: uuid.UUID,
        new_status: OrderStatus,
        executed_quantity: Optional[Decimal] = None,
        executed_price: Optional[Decimal] = None,
        commission: Optional[Decimal] = None,
        commission_asset: str = "USDT",
        reason: Optional[str] = None
    ) -> Order:
        """Execute update order status use case."""
        
        # Get order
        order = await self._order_repository.get_by_id(order_id, user_id)
        if not order:
            raise NotFoundError("Order not found")
        
        # Update order based on status
        if new_status == OrderStatus.FILLED:
            if executed_quantity is None or executed_price is None:
                raise ValidationError("Executed quantity and price required for filled orders")
            
            remaining_qty = order.get_remaining_quantity()
            order.fill(
                executed_quantity=min(executed_quantity, remaining_qty),
                executed_price=executed_price,
                commission=commission or Decimal("0"),
                commission_asset=commission_asset
            )
            
        elif new_status == OrderStatus.PARTIALLY_FILLED:
            if executed_quantity is None or executed_price is None:
                raise ValidationError("Executed quantity and price required for partial fills")
            
            order.fill(
                executed_quantity=executed_quantity,
                executed_price=executed_price,
                commission=commission or Decimal("0"),
                commission_asset=commission_asset
            )
            
        elif new_status == OrderStatus.CANCELLED:
            order.cancel(reason)
            
        elif new_status == OrderStatus.REJECTED:
            if reason is None:
                reason = "Order rejected by exchange"
            order.reject(reason)
            
        else:
            # For other status updates, just update the status
            order.status = new_status
            order.updated_at = dt.now(dt_timezone.utc)
        
        # Save updated order
        await self._order_repository.update(order)
        
        logger.info(f"Order {order_id} status updated to {new_status}")
        return order
