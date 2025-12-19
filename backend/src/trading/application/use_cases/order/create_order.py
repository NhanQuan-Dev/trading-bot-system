"""Create order use case."""
from typing import Dict, Any
from decimal import Decimal
import uuid
import logging

from ....domain.order import Order, OrderType, OrderSide, PositionSide, TimeInForce
from ....interfaces.repositories.order_repository import IOrderRepository
from ....interfaces.repositories.exchange_repository import IExchangeRepository
from ....infrastructure.exchange.exchange_manager import ExchangeManager
from ....shared.exceptions.business import ValidationError, ExchangeConnectionError

logger = logging.getLogger(__name__)


class CreateOrderUseCase:
    """Use case for creating new orders."""
    
    def __init__(
        self,
        order_repository: IOrderRepository,
        exchange_repository: IExchangeRepository,
        exchange_manager: ExchangeManager,
    ):
        self._order_repository = order_repository
        self._exchange_repository = exchange_repository
        self._exchange_manager = exchange_manager
    
    async def execute(
        self,
        user_id: uuid.UUID,
        exchange_connection_id: uuid.UUID,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        quantity: Decimal,
        price: Decimal = None,
        stop_price: Decimal = None,
        position_side: PositionSide = PositionSide.BOTH,
        time_in_force: TimeInForce = TimeInForce.GTC,
        reduce_only: bool = False,
        leverage: int = 1,
        client_order_id: str = None,
        **kwargs
    ) -> Order:
        """Execute create order use case."""
        
        # Validate exchange connection
        connection = await self._exchange_repository.find_by_id(exchange_connection_id)
        if not connection or connection.user_id != user_id:
            raise ValidationError("Invalid exchange connection")
        
        if not connection.is_connected() or not connection.can_trade():
            raise ExchangeConnectionError("Exchange connection not available for trading")
        
        # Create order entity
        if order_type == OrderType.MARKET:
            order = Order.create_market_order(
                user_id=user_id,
                exchange_connection_id=exchange_connection_id,
                symbol=symbol,
                side=side,
                quantity=quantity,
                position_side=position_side,
                reduce_only=reduce_only,
                leverage=leverage,
            )
        elif order_type == OrderType.LIMIT:
            if price is None:
                raise ValidationError("Price is required for limit orders")
            order = Order.create_limit_order(
                user_id=user_id,
                exchange_connection_id=exchange_connection_id,
                symbol=symbol,
                side=side,
                quantity=quantity,
                price=price,
                position_side=position_side,
                time_in_force=time_in_force,
                reduce_only=reduce_only,
                leverage=leverage,
            )
        elif order_type == OrderType.STOP_MARKET:
            if stop_price is None:
                raise ValidationError("Stop price is required for stop market orders")
            order = Order.create_stop_market_order(
                user_id=user_id,
                exchange_connection_id=exchange_connection_id,
                symbol=symbol,
                side=side,
                quantity=quantity,
                stop_price=stop_price,
                position_side=position_side,
                reduce_only=reduce_only,
                leverage=leverage,
            )
        else:
            raise ValidationError(f"Order type {order_type} not supported")
        
        # Set optional fields
        if client_order_id:
            order.client_order_id = client_order_id
        
        # Save order first
        created_order = await self._order_repository.create(order)
        
        try:
            # Submit to exchange
            exchange_client = self._exchange_manager.get_client(connection.exchange_type)
            await exchange_client.set_credentials(
                connection.api_key_decrypted,
                connection.secret_key_decrypted,
                connection.testnet
            )
            
            # Convert order to exchange parameters
            order_params = created_order.to_exchange_params()
            
            # Submit order to exchange
            exchange_result = await exchange_client.place_order(**order_params)
            
            # Update order with exchange response
            created_order.submit(
                exchange_order_id=exchange_result['orderId'],
                client_order_id=exchange_result.get('clientOrderId')
            )
            
            # Save updated order
            await self._order_repository.update(created_order)
            
            logger.info(f"Order {created_order.id} created and submitted to exchange")
            return created_order
            
        except Exception as e:
            # Mark order as rejected
            created_order.reject(str(e))
            await self._order_repository.update(created_order)
            
            logger.error(f"Failed to submit order {created_order.id} to exchange: {e}")
            raise ExchangeConnectionError(f"Failed to submit order to exchange: {e}")
