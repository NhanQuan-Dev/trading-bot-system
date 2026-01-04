from typing import List, Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy.orm import selectinload
from trading.domain.order import (
    Order, OrderSide, OrderType, OrderStatus, TimeInForce,
    PositionSide, OrderQuantity, OrderPrice, WorkingType,
    OrderExecution
)
from decimal import Decimal
import uuid
from ..models.trading_models import OrderModel

class OrderRepository:
    """Repository for managing Order entities."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        
    def _to_domain(self, model: OrderModel) -> Order:
        """Convert OrderModel to Order domain entity."""
        meta_data = model.meta_data or {}
        
        # Recover exchange_connection_id from bot if available
        exchange_connection_id = uuid.uuid4() # Fallback
        if model.bot and model.bot.exchange_connection_id:
             exchange_connection_id = model.bot.exchange_connection_id
             
        # Reconstruct Values
        quantity = OrderQuantity(Decimal(str(model.quantity)))
        price = OrderPrice(Decimal(str(model.price))) if model.price else None
        stop_price = OrderPrice(Decimal(str(model.stop_price))) if model.stop_price else None
        
        # Reconstruct Execution
        execution = OrderExecution(
            executed_quantity=Decimal(str(model.filled_quantity or 0)),
            avg_price=Decimal(str(model.filled_avg_price)) if model.filled_avg_price else None
        )
        
        return Order(
            id=model.id,
            user_id=model.user_id,
            exchange_connection_id=exchange_connection_id,
            exchange_id=model.exchange_id,
            symbol=model.symbol,
            side=OrderSide(model.side),
            order_type=OrderType(model.order_type),
            quantity=quantity,
            status=OrderStatus(model.status),
            created_at=model.created_at,
            updated_at=model.updated_at,
            bot_id=model.bot_id,
            price=price,
            stop_price=stop_price,
            callback_rate=model.callback_rate,
            leverage=model.leverage,
            margin_type=model.margin_mode, 
            position_side=PositionSide(meta_data.get('position_side', 'BOTH')),
            reduce_only=meta_data.get('reduce_only', False),
            time_in_force=TimeInForce(model.time_in_force),


            close_position=meta_data.get('close_position', False) or (True if model.position_id else False),

            position_id=model.position_id,
            client_order_id=model.client_order_id,
            exchange_order_id=model.exchange_order_id,
            execution=execution,
            error_message=meta_data.get('error_message'),
            meta_data=meta_data,
            filled_at=model.filled_at,
            cancelled_at=model.cancelled_at
        )

    async def add(self, order: OrderModel) -> OrderModel:
        """Add a new order to the database."""
        self.session.add(order)
        await self.session.commit()
        await self.session.refresh(order)
        return order
        
    async def create(self, order: Order) -> Order:
        """Create a new order from domain entity."""
        # Map Entity to Model
        meta_data = order.meta_data or {}
        # Store non-mapped fields in metadata
        if order.position_side:
            meta_data['position_side'] = order.position_side.value
        if order.reduce_only:
            meta_data['reduce_only'] = order.reduce_only

        if order.error_message:
            meta_data['error_message'] = order.error_message
        if order.close_position:
            meta_data['close_position'] = True


        model = OrderModel(
            id=order.id,
            user_id=order.user_id,

            bot_id=order.bot_id,
            position_id=order.position_id,
            exchange_id=order.exchange_id,
            symbol=order.symbol,
            side=order.side.value,
            order_type=order.order_type.value,
            quantity=order.quantity.value,
            status=order.status.value,
            created_at=order.created_at,
            updated_at=order.updated_at,
            price=order.price.value if order.price else None,
            stop_price=order.stop_price.value if order.stop_price else None,
            callback_rate=order.callback_rate,
            leverage=order.leverage,
            # Map margin_type (Entity) to margin_mode (Model)
            margin_mode=order.margin_type if hasattr(order, 'margin_type') else "ISOLATED",
            time_in_force=order.time_in_force.value,
            # We default position_mode mostly to ONE_WAY unless implied strictly
            # But usually this is an Account setting. We can default to ONE_WAY or HEDGE based on data?
            # Model default is ONE_WAY.
            meta_data=meta_data,
            client_order_id=order.client_order_id,  # CRITICAL: Must store for WebSocket lookup
            exchange_order_id=order.exchange_order_id
        )
            
        self.session.add(model)
        await self.session.commit()
        return order

    async def update(self, order: Order) -> Order:
        """Update an existing order from domain entity."""
        stmt = select(OrderModel).where(OrderModel.id == order.id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            # If not found, maybe create? But usually update implies existing.
            raise ValueError(f"Order {order.id} not found")
            
        # Update fields
        model.status = order.status.value
        if order.exchange_order_id:
            model.exchange_order_id = order.exchange_order_id
            
        if order.execution:
            model.filled_quantity = order.execution.executed_quantity
            model.filled_avg_price = order.execution.avg_price
        
        if order.filled_at:
            model.filled_at = order.filled_at
            
        # Update metadata for error message
        if order.error_message:
             meta = dict(model.meta_data) if model.meta_data else {}
             meta['error_message'] = order.error_message
             model.meta_data = meta
             
        model.updated_at = order.updated_at
        
        await self.session.commit()
        return order

    async def find_by_bot_id(self, bot_id: UUID) -> List[OrderModel]:
        """Find all orders for a specific bot."""
        stmt = select(OrderModel).where(OrderModel.bot_id == bot_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
        
    async def get_by_id(self, order_id: UUID, user_id: UUID) -> Optional[Order]:
        """Get order by ID and user ID."""
        stmt = select(OrderModel).options(selectinload(OrderModel.bot)).where(
            OrderModel.id == order_id,
            OrderModel.user_id == user_id
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def get_by_client_order_id(self, client_order_id: str, user_id: UUID) -> Optional[Order]:
        """Get order by client order ID."""
        stmt = select(OrderModel).options(selectinload(OrderModel.bot)).where(
            OrderModel.client_order_id == client_order_id,
            OrderModel.user_id == user_id
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def get_by_exchange_order_id(self, exchange_order_id: str, user_id: UUID) -> Optional[Order]:
        """Get order by exchange order ID."""
        stmt = select(OrderModel).options(selectinload(OrderModel.bot)).where(
            OrderModel.exchange_order_id == exchange_order_id,
            OrderModel.user_id == user_id
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None
