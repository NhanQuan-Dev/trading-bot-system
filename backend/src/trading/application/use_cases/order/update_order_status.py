"""Update order status use case."""
import uuid
import logging
from decimal import Decimal
from typing import Optional
from datetime import datetime as dt, timezone as dt_timezone

from ....domain.order import Order, OrderStatus
from ....interfaces.repositories.order_repository import IOrderRepository
from ....interfaces.repositories.trade_repository import ITradeRepository
from ....domain.trade import Trade
from ....shared.exceptions.business import NotFoundError, ValidationError
from ...services.bot_stats_service import BotStatsService
from ....infrastructure.websocket.websocket_manager import websocket_manager

logger = logging.getLogger(__name__)


class UpdateOrderStatusUseCase:
    """Use case for updating order status (typically from exchange events)."""
    
    def __init__(
        self, 
        order_repository: IOrderRepository,
        trade_repository: Optional[ITradeRepository] = None, # Make optional for backward compatibility if needed, or require it
        bot_stats_service: Optional[BotStatsService] = None
    ):
        self._order_repository = order_repository
        self._trade_repository = trade_repository
        self._bot_stats_service = bot_stats_service
    
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

            
            # === NEW: Create Trade Record ===
            if self._trade_repository:
                try:
                    # Determine P&L for this trade (simplified)
                    trade_pnl = Decimal("0") # Default
                    # If this is a closing order, we can try calculate P&L
                    if order.close_position:
                         # Use similar logic to stats service
                         entry_price_val = order.meta_data.get("entry_price")
                         if entry_price_val:
                             ep = Decimal(str(entry_price_val))
                             # Side check
                             order_side = order.side.value if hasattr(order.side, 'value') else str(order.side)
                             if order_side == "SELL":
                                 trade_pnl = (executed_price - ep) * executed_quantity - (commission or 0)
                             else:
                                 trade_pnl = (ep - executed_price) * executed_quantity - (commission or 0)
                                 
                    new_trade = Trade.create(
                        order_id=order.id,
                        user_id=user_id,
                        symbol=order.symbol,
                        side=order.side,
                        price=executed_price,
                        quantity=executed_quantity,
                        commission=commission or Decimal("0"),
                        commission_asset=commission_asset,
                        realized_pnl=trade_pnl,
                        bot_id=order.bot_id
                    )
                    await self._trade_repository.create(new_trade)
                    logger.info(f"Trade created for order {order_id}")
                except Exception as e:
                    logger.error(f"Failed to create trade record: {e}")

            # === NEW: Update bot stats if this is a close_position order ===
            logger.info(f"DEBUG: Checking Stats trigger for Order {order.id}: close_pos={order.close_position}, bot_id={order.bot_id}, has_service={self._bot_stats_service is not None}")
            if order.close_position and order.bot_id and self._bot_stats_service:
                await self._update_bot_stats_on_close(
                    order=order,
                    user_id=user_id,
                    executed_quantity=executed_quantity,
                    executed_price=executed_price,
                    commission=commission or Decimal("0")
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
    
    async def _update_bot_stats_on_close(
        self,
        order: Order,
        user_id: uuid.UUID,
        executed_quantity: Decimal,
        executed_price: Decimal,
        commission: Decimal
    ):
        """Update bot stats when a close_position order is filled."""
        try:
            bot_id = str(order.bot_id)
            
            # Calculate realized P&L
            # For close orders, we need entry price from metadata or position
            entry_price = order.meta_data.get("entry_price") if order.meta_data else None
            
            if entry_price:
                entry_price = Decimal(str(entry_price))
                # Determine P&L based on side (SELL = closing LONG, BUY = closing SHORT)
                if order.side == "SELL":
                    # Closing LONG: P&L = (exit - entry) * qty
                    realized_pnl = (executed_price - entry_price) * executed_quantity - commission
                else:
                    # Closing SHORT: P&L = (entry - exit) * qty
                    realized_pnl = (entry_price - executed_price) * executed_quantity - commission
            else:
                # Fallback: use order's realized_pnl if available
                realized_pnl = order.meta_data.get("realized_pnl", Decimal("0")) if order.meta_data else Decimal("0")
                if isinstance(realized_pnl, (int, float, str)):
                    realized_pnl = Decimal(str(realized_pnl))
            
            # Update bot stats
            success = await self._bot_stats_service.update_stats_on_trade_close(
                bot_id=bot_id,
                realized_pnl=realized_pnl
            )
            
            if success:
                # Broadcast stats update via WebSocket
                stats = await self._bot_stats_service.get_bot_stats(bot_id)
                if stats:
                    await websocket_manager.broadcast_bot_stats_update(
                        user_id=str(user_id),
                        bot_id=bot_id,
                        stats=stats
                    )
                    logger.info(f"Bot stats updated and broadcasted for bot {bot_id}")
                    
        except Exception as e:
            # Don't fail the order update if stats update fails
            logger.error(f"Failed to update bot stats on position close: {e}")

