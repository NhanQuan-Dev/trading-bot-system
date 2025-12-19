"""Cancel order use case."""
import uuid
import logging

from ....domain.order import Order, OrderStatus
from ....interfaces.repositories.order_repository import IOrderRepository
from ....interfaces.repositories.exchange_repository import IExchangeRepository
from ....infrastructure.exchange.exchange_manager import ExchangeManager
from ....shared.exceptions.business import ValidationError, ExchangeConnectionError, NotFoundError

logger = logging.getLogger(__name__)


class CancelOrderUseCase:
    """Use case for cancelling orders."""
    
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
        order_id: uuid.UUID,
        reason: str = None
    ) -> Order:
        """Execute cancel order use case."""
        
        # Get order
        order = await self._order_repository.get_by_id(order_id, user_id)
        if not order:
            raise NotFoundError("Order not found")
        
        # Check if order can be cancelled
        if not order.is_active():
            raise ValidationError(f"Cannot cancel order in {order.status} status")
        
        # Get exchange connection
        connection = await self._exchange_repository.find_by_id(order.exchange_connection_id)
        if not connection or not connection.is_connected():
            raise ExchangeConnectionError("Exchange connection not available")
        
        try:
            # Cancel on exchange if order was submitted
            if order.exchange_order_id:
                exchange_client = self._exchange_manager.get_client(connection.exchange_type)
                await exchange_client.set_credentials(
                    connection.api_key_decrypted,
                    connection.secret_key_decrypted,
                    connection.testnet
                )
                
                await exchange_client.cancel_order(
                    symbol=order.symbol,
                    order_id=order.exchange_order_id
                )
                
                logger.info(f"Order {order.id} cancelled on exchange")
            
            # Update order status
            order.cancel(reason)
            
            # Save updated order
            await self._order_repository.update(order)
            
            logger.info(f"Order {order.id} cancelled successfully")
            return order
            
        except Exception as e:
            logger.error(f"Failed to cancel order {order.id}: {e}")
            raise ExchangeConnectionError(f"Failed to cancel order on exchange: {e}")
