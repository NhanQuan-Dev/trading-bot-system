"""SQLAlchemy Order repository implementation."""
from typing import List, Optional, Dict, Any
from datetime import datetime as dt
from decimal import Decimal
import uuid
import json
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, desc, func, text
from sqlalchemy.orm import selectinload, joinedload

from ...interfaces.repositories.order_repository import IOrderRepository
from ...domain.order import (
    Order, 
    OrderStatus, 
    OrderSide, 
    OrderType, 
    TimeInForce,
    PositionSide,
    WorkingType,
    OrderPrice,
    OrderQuantity,
    OrderExecution
)
from ..persistence.models.trading_models import OrderModel


logger = logging.getLogger(__name__)


class OrderRepository(IOrderRepository):
    """SQLAlchemy implementation of order repository."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    def _map_to_domain(self, model: OrderModel) -> Order:
        """Map database model to domain entity."""
        # Parse execution details from database
        execution = OrderExecution()
        if model.executed_quantity:
            execution = OrderExecution(
                executed_quantity=Decimal(str(model.executed_quantity)),
                executed_quote=Decimal(str(model.executed_quote or 0)),
                avg_price=Decimal(str(model.avg_price)) if model.avg_price else None,
                commission=Decimal(str(model.commission or 0)),
                commission_asset=model.commission_asset or "USDT",
            )
        
        return Order(
            id=model.id,
            user_id=model.user_id,
            bot_id=model.bot_id,
            exchange_connection_id=model.exchange_connection_id,
            symbol=model.symbol,
            side=OrderSide(model.side),
            order_type=OrderType(model.order_type),
            quantity=OrderQuantity(Decimal(str(model.quantity))),
            price=OrderPrice(Decimal(str(model.price))) if model.price else None,
            stop_price=OrderPrice(Decimal(str(model.stop_price))) if model.stop_price else None,
            callback_rate=Decimal(str(model.callback_rate)) if model.callback_rate else None,
            position_side=PositionSide(model.position_side),
            time_in_force=TimeInForce(model.time_in_force),
            reduce_only=model.reduce_only,
            close_position=model.close_position,
            working_type=WorkingType(model.working_type),
            price_protect=model.price_protect,
            status=OrderStatus(model.status),
            exchange_order_id=model.exchange_order_id,
            client_order_id=model.client_order_id,
            execution=execution,
            leverage=model.leverage,
            margin_type=model.margin_type,
            error_message=model.error_message,
            meta_data=json.loads(model.meta_data) if model.meta_data else {},
            created_at=model.created_at,
            updated_at=model.updated_at,
            submitted_at=model.submitted_at,
            filled_at=model.filled_at,
            cancelled_at=model.cancelled_at,
        )
    
    def _map_to_model(self, order: Order) -> Dict[str, Any]:
        """Map domain entity to database model data."""
        return {
            "id": order.id,
            "user_id": order.user_id,
            "bot_id": order.bot_id,
            "exchange_connection_id": order.exchange_connection_id,
            "symbol": order.symbol,
            "side": order.side.value,
            "order_type": order.order_type.value,
            "quantity": float(order.quantity.value),
            "price": float(order.price.value) if order.price else None,
            "stop_price": float(order.stop_price.value) if order.stop_price else None,
            "callback_rate": float(order.callback_rate) if order.callback_rate else None,
            "position_side": order.position_side.value,
            "time_in_force": order.time_in_force.value,
            "reduce_only": order.reduce_only,
            "close_position": order.close_position,
            "working_type": order.working_type.value,
            "price_protect": order.price_protect,
            "status": order.status.value,
            "exchange_order_id": order.exchange_order_id,
            "client_order_id": order.client_order_id,
            "executed_quantity": float(order.execution.executed_quantity) if order.execution else 0,
            "executed_quote": float(order.execution.executed_quote) if order.execution else 0,
            "avg_price": float(order.execution.avg_price) if order.execution and order.execution.avg_price else None,
            "commission": float(order.execution.commission) if order.execution else 0,
            "commission_asset": order.execution.commission_asset if order.execution else "USDT",
            "leverage": order.leverage,
            "margin_type": order.margin_type,
            "error_message": order.error_message,
            "meta_data": json.dumps(order.meta_data) if order.meta_data else None,
            "created_at": order.created_at,
            "updated_at": order.updated_at,
            "submitted_at": order.submitted_at,
            "filled_at": order.filled_at,
            "cancelled_at": order.cancelled_at,
        }
    
    async def create(self, order: Order) -> Order:
        """Create a new order."""
        try:
            model_data = self._map_to_model(order)
            model = OrderModel(**model_data)
            
            self.session.add(model)
            await self.session.flush()
            await self.session.refresh(model)
            
            logger.info(f"Created order {order.id} for user {order.user_id}")
            return self._map_to_domain(model)
            
        except Exception as e:
            logger.error(f"Failed to create order: {e}")
            raise
    
    async def get_by_id(self, order_id: uuid.UUID, user_id: uuid.UUID) -> Optional[Order]:
        """Get order by ID and user ID."""
        try:
            stmt = select(OrderModel).where(
                and_(OrderModel.id == order_id, OrderModel.user_id == user_id)
            )
            result = await self.session.execute(stmt)
            model = result.scalar_one_or_none()
            
            return self._map_to_domain(model) if model else None
            
        except Exception as e:
            logger.error(f"Failed to get order {order_id}: {e}")
            return None
    
    async def get_by_exchange_order_id(
        self, 
        exchange_order_id: str, 
        user_id: uuid.UUID
    ) -> Optional[Order]:
        """Get order by exchange order ID."""
        try:
            stmt = select(OrderModel).where(
                and_(
                    OrderModel.exchange_order_id == exchange_order_id,
                    OrderModel.user_id == user_id
                )
            )
            result = await self.session.execute(stmt)
            model = result.scalar_one_or_none()
            
            return self._map_to_domain(model) if model else None
            
        except Exception as e:
            logger.error(f"Failed to get order by exchange ID {exchange_order_id}: {e}")
            return None
    
    async def get_by_client_order_id(
        self,
        client_order_id: str,
        user_id: uuid.UUID
    ) -> Optional[Order]:
        """Get order by client order ID."""
        try:
            stmt = select(OrderModel).where(
                and_(
                    OrderModel.client_order_id == client_order_id,
                    OrderModel.user_id == user_id
                )
            )
            result = await self.session.execute(stmt)
            model = result.scalar_one_or_none()
            
            return self._map_to_domain(model) if model else None
            
        except Exception as e:
            logger.error(f"Failed to get order by client ID {client_order_id}: {e}")
            return None
    
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
        try:
            stmt = select(OrderModel).where(OrderModel.user_id == user_id)
            
            if status:
                stmt = stmt.where(OrderModel.status == status.value)
            
            if symbol:
                stmt = stmt.where(OrderModel.symbol == symbol)
            
            if bot_id:
                stmt = stmt.where(OrderModel.bot_id == bot_id)
            
            stmt = stmt.order_by(desc(OrderModel.created_at))
            stmt = stmt.limit(limit).offset(offset)
            
            result = await self.session.execute(stmt)
            models = result.scalars().all()
            
            return [self._map_to_domain(model) for model in models]
            
        except Exception as e:
            logger.error(f"Failed to list orders for user {user_id}: {e}")
            return []
    
    async def list_active_by_user(self, user_id: uuid.UUID) -> List[Order]:
        """List active orders by user."""
        try:
            active_statuses = [
                OrderStatus.PENDING.value,
                OrderStatus.NEW.value,
                OrderStatus.PARTIALLY_FILLED.value
            ]
            
            stmt = select(OrderModel).where(
                and_(
                    OrderModel.user_id == user_id,
                    OrderModel.status.in_(active_statuses)
                )
            ).order_by(desc(OrderModel.created_at))
            
            result = await self.session.execute(stmt)
            models = result.scalars().all()
            
            return [self._map_to_domain(model) for model in models]
            
        except Exception as e:
            logger.error(f"Failed to list active orders for user {user_id}: {e}")
            return []
    
    async def list_by_bot(self, bot_id: uuid.UUID) -> List[Order]:
        """List orders by bot."""
        try:
            stmt = select(OrderModel).where(
                OrderModel.bot_id == bot_id
            ).order_by(desc(OrderModel.created_at))
            
            result = await self.session.execute(stmt)
            models = result.scalars().all()
            
            return [self._map_to_domain(model) for model in models]
            
        except Exception as e:
            logger.error(f"Failed to list orders for bot {bot_id}: {e}")
            return []
    
    async def update(self, order: Order) -> Order:
        """Update an existing order."""
        try:
            model_data = self._map_to_model(order)
            
            # Remove id to avoid updating it
            order_id = model_data.pop("id")
            
            stmt = update(OrderModel).where(
                and_(
                    OrderModel.id == order_id,
                    OrderModel.user_id == order.user_id
                )
            ).values(**model_data)
            
            await self.session.execute(stmt)
            
            # Get updated model
            updated_order = await self.get_by_id(order.id, order.user_id)
            if updated_order:
                logger.info(f"Updated order {order.id}")
                return updated_order
            else:
                raise ValueError(f"Order {order.id} not found after update")
            
        except Exception as e:
            logger.error(f"Failed to update order {order.id}: {e}")
            raise
    
    async def update_status(
        self, 
        order_id: uuid.UUID, 
        user_id: uuid.UUID, 
        status: OrderStatus,
        error_message: Optional[str] = None
    ) -> Optional[Order]:
        """Update order status."""
        try:
            update_data = {
                "status": status.value,
                "updated_at": dt.now(),
            }
            
            if error_message:
                update_data["error_message"] = error_message
            
            if status == OrderStatus.CANCELLED:
                update_data["cancelled_at"] = dt.now()
            elif status == OrderStatus.FILLED:
                update_data["filled_at"] = dt.now()
            
            stmt = update(OrderModel).where(
                and_(
                    OrderModel.id == order_id,
                    OrderModel.user_id == user_id
                )
            ).values(**update_data)
            
            await self.session.execute(stmt)
            
            return await self.get_by_id(order_id, user_id)
            
        except Exception as e:
            logger.error(f"Failed to update order status {order_id}: {e}")
            return None
    
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
        try:
            # Get current order to calculate new totals
            current_order = await self.get_by_id(order_id, user_id)
            if not current_order:
                return None
            
            # Calculate new totals
            new_executed_quantity = current_order.execution.executed_quantity + Decimal(str(executed_quantity))
            new_executed_quote = current_order.execution.executed_quote + (Decimal(str(executed_quantity)) * Decimal(str(executed_price)))
            new_avg_price = new_executed_quote / new_executed_quantity if new_executed_quantity > 0 else None
            new_commission = current_order.execution.commission + Decimal(str(commission))
            
            # Determine new status
            if new_executed_quantity >= current_order.quantity.value:
                new_status = OrderStatus.FILLED
                filled_at = dt.now()
            else:
                new_status = OrderStatus.PARTIALLY_FILLED
                filled_at = None
            
            update_data = {
                "executed_quantity": float(new_executed_quantity),
                "executed_quote": float(new_executed_quote),
                "avg_price": float(new_avg_price) if new_avg_price else None,
                "commission": float(new_commission),
                "commission_asset": commission_asset,
                "status": new_status.value,
                "updated_at": dt.now(),
            }
            
            if filled_at:
                update_data["filled_at"] = filled_at
            
            stmt = update(OrderModel).where(
                and_(
                    OrderModel.id == order_id,
                    OrderModel.user_id == user_id
                )
            ).values(**update_data)
            
            await self.session.execute(stmt)
            
            return await self.get_by_id(order_id, user_id)
            
        except Exception as e:
            logger.error(f"Failed to update order execution {order_id}: {e}")
            return None
    
    async def cancel_order(
        self, 
        order_id: uuid.UUID, 
        user_id: uuid.UUID,
        reason: Optional[str] = None
    ) -> Optional[Order]:
        """Cancel an order."""
        return await self.update_status(order_id, user_id, OrderStatus.CANCELLED, reason)
    
    async def cancel_all_by_symbol(
        self,
        user_id: uuid.UUID,
        symbol: str
    ) -> List[Order]:
        """Cancel all active orders for a symbol."""
        try:
            # Get all active orders for symbol
            active_orders = await self.list_by_user(
                user_id=user_id,
                symbol=symbol,
                status=None  # We'll filter active ones below
            )
            
            # Filter only active orders and cancel them
            cancelled_orders = []
            for order in active_orders:
                if order.is_active():
                    cancelled_order = await self.cancel_order(
                        order.id, 
                        user_id, 
                        f"Cancelled all orders for symbol {symbol}"
                    )
                    if cancelled_order:
                        cancelled_orders.append(cancelled_order)
            
            return cancelled_orders
            
        except Exception as e:
            logger.error(f"Failed to cancel all orders for symbol {symbol}: {e}")
            return []
    
    async def cancel_all_by_bot(self, bot_id: uuid.UUID) -> List[Order]:
        """Cancel all active orders for a bot."""
        try:
            # Get all orders for bot
            bot_orders = await self.list_by_bot(bot_id)
            
            # Cancel active orders
            cancelled_orders = []
            for order in bot_orders:
                if order.is_active():
                    cancelled_order = await self.cancel_order(
                        order.id,
                        order.user_id,
                        f"Cancelled all orders for bot {bot_id}"
                    )
                    if cancelled_order:
                        cancelled_orders.append(cancelled_order)
            
            return cancelled_orders
            
        except Exception as e:
            logger.error(f"Failed to cancel all orders for bot {bot_id}: {e}")
            return []
    
    async def get_order_count(self, user_id: uuid.UUID, status: Optional[OrderStatus] = None) -> int:
        """Get order count for user."""
        try:
            stmt = select(func.count(OrderModel.id)).where(OrderModel.user_id == user_id)
            
            if status:
                stmt = stmt.where(OrderModel.status == status.value)
            
            result = await self.session.execute(stmt)
            return result.scalar() or 0
            
        except Exception as e:
            logger.error(f"Failed to get order count for user {user_id}: {e}")
            return 0
    
    async def get_volume_stats(
        self,
        user_id: uuid.UUID,
        symbol: Optional[str] = None,
        start_date: Optional[dt] = None,
        end_date: Optional[dt] = None
    ) -> Dict[str, Any]:
        """Get volume statistics for user."""
        try:
            stmt = select(
                func.count(OrderModel.id).label("total_orders"),
                func.coalesce(func.sum(OrderModel.executed_quote), 0).label("total_volume"),
                func.coalesce(func.sum(OrderModel.commission), 0).label("total_commission"),
                func.coalesce(func.avg(OrderModel.executed_quote), 0).label("avg_order_size"),
            ).where(OrderModel.user_id == user_id)
            
            if symbol:
                stmt = stmt.where(OrderModel.symbol == symbol)
            
            if start_date:
                stmt = stmt.where(OrderModel.created_at >= start_date)
            
            if end_date:
                stmt = stmt.where(OrderModel.created_at <= end_date)
            
            # Only include filled orders for volume stats
            stmt = stmt.where(OrderModel.status.in_([
                OrderStatus.FILLED.value,
                OrderStatus.PARTIALLY_FILLED.value
            ]))
            
            result = await self.session.execute(stmt)
            row = result.first()
            
            return {
                "total_orders": row.total_orders if row else 0,
                "total_volume": float(row.total_volume if row else 0),
                "total_commission": float(row.total_commission if row else 0),
                "avg_order_size": float(row.avg_order_size if row else 0),
            }
            
        except Exception as e:
            logger.error(f"Failed to get volume stats for user {user_id}: {e}")
            return {
                "total_orders": 0,
                "total_volume": 0.0,
                "total_commission": 0.0,
                "avg_order_size": 0.0,
            }
    
    async def find_by_filters(
        self,
        filters: Dict[str, Any],
        limit: int = 100,
        offset: int = 0,
        order_by: str = "created_at",
        desc: bool = True
    ) -> List[Order]:
        """Find orders by filters."""
        try:
            stmt = select(OrderModel)
            
            # Apply filters
            if "user_id" in filters:
                stmt = stmt.where(OrderModel.user_id == filters["user_id"])
            
            if "status" in filters:
                stmt = stmt.where(OrderModel.status == filters["status"].value)
            
            if "symbol" in filters:
                stmt = stmt.where(OrderModel.symbol == filters["symbol"])
            
            if "side" in filters:
                stmt = stmt.where(OrderModel.side == filters["side"].value)
            
            if "exchange_connection_id" in filters:
                stmt = stmt.where(OrderModel.exchange_connection_id == filters["exchange_connection_id"])
            
            if "bot_id" in filters:
                stmt = stmt.where(OrderModel.bot_id == filters["bot_id"])
            
            if "start_time" in filters:
                stmt = stmt.where(OrderModel.created_at >= filters["start_time"])
            
            if "end_time" in filters:
                stmt = stmt.where(OrderModel.created_at <= filters["end_time"])
            
            # Apply ordering
            if hasattr(OrderModel, order_by):
                order_col = getattr(OrderModel, order_by)
                if desc:
                    stmt = stmt.order_by(desc(order_col))
                else:
                    stmt = stmt.order_by(order_col)
            
            # Apply pagination
            stmt = stmt.limit(limit).offset(offset)
            
            result = await self.session.execute(stmt)
            models = result.scalars().all()
            
            return [self._to_domain(model) for model in models]
            
        except Exception as e:
            logger.error(f"Failed to find orders by filters: {e}")
            return []
    
    async def count_by_filters(self, filters: Dict[str, Any]) -> int:
        """Count orders by filters."""
        try:
            stmt = select(func.count(OrderModel.id))
            
            # Apply same filters as find_by_filters
            if "user_id" in filters:
                stmt = stmt.where(OrderModel.user_id == filters["user_id"])
            
            if "status" in filters:
                stmt = stmt.where(OrderModel.status == filters["status"].value)
            
            if "symbol" in filters:
                stmt = stmt.where(OrderModel.symbol == filters["symbol"])
            
            if "side" in filters:
                stmt = stmt.where(OrderModel.side == filters["side"].value)
            
            if "exchange_connection_id" in filters:
                stmt = stmt.where(OrderModel.exchange_connection_id == filters["exchange_connection_id"])
            
            if "bot_id" in filters:
                stmt = stmt.where(OrderModel.bot_id == filters["bot_id"])
            
            if "start_time" in filters:
                stmt = stmt.where(OrderModel.created_at >= filters["start_time"])
            
            if "end_time" in filters:
                stmt = stmt.where(OrderModel.created_at <= filters["end_time"])
            
            result = await self.session.execute(stmt)
            return result.scalar() or 0
            
        except Exception as e:
            logger.error(f"Failed to count orders by filters: {e}")
            return 0