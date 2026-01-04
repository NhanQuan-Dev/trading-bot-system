"""Modify order use case - implements cancel-and-replace pattern.

Binance does not support direct order modification. To modify an order:
1. Cancel the existing order on exchange
2. Create a new order with updated parameters
3. Update database to reflect changes
"""
from typing import Dict, Any, Optional
from decimal import Decimal
import uuid
import logging

from ....domain.order import Order, OrderStatus, OrderQuantity, OrderPrice
from ....interfaces.repositories.order_repository import IOrderRepository
from ....interfaces.repositories.exchange_repository import IExchangeRepository
from ....infrastructure.exchange.exchange_manager import ExchangeManager
from ....shared.exceptions.business import ValidationError, ExchangeConnectionError

logger = logging.getLogger(__name__)


class ModifyOrderUseCase:
    """
    Use case for modifying existing orders using cancel-and-replace pattern.
    
    Since Binance doesn't support direct order modification, this use case:
    1. Cancels the original order on the exchange
    2. Creates a new order with the updated parameters
    3. Links the new order to the original for traceability
    """
    
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
        new_quantity: Optional[Decimal] = None,
        new_price: Optional[Decimal] = None,
        new_stop_price: Optional[Decimal] = None,
    ) -> Order:
        """
        Execute modify order use case.
        
        Args:
            user_id: The user making the modification
            order_id: The order to modify
            new_quantity: New quantity (optional)
            new_price: New price for limit orders (optional)
            new_stop_price: New stop price for stop orders (optional)
        
        Returns:
            The new replacement order
            
        Raises:
            ValidationError: If order cannot be modified
            ExchangeConnectionError: If exchange operation fails
        """
        # Get existing order
        original_order = await self._order_repository.find_by_id(order_id)
        if not original_order:
            raise ValidationError("Order not found")
        
        if original_order.user_id != user_id:
            raise ValidationError("Order not found")  # Don't leak info
        
        # Check if order can be modified
        if not original_order.is_active():
            raise ValidationError(
                f"Cannot modify order with status {original_order.status.value}. "
                "Only active orders (PENDING, NEW, PARTIALLY_FILLED) can be modified."
            )
        
        # Must have at least one modification
        if new_quantity is None and new_price is None and new_stop_price is None:
            raise ValidationError("No modifications specified")
        
        # Get exchange connection
        connection = await self._exchange_repository.find_by_id(
            original_order.exchange_connection_id
        )
        if not connection:
            raise ExchangeConnectionError("Exchange connection not found")
        
        if not connection.is_connected():
            raise ExchangeConnectionError("Exchange connection not available")
        
        # Get exchange client
        exchange_client = self._exchange_manager.get_client(connection.exchange_type)
        await exchange_client.set_credentials(
            connection.api_key_decrypted,
            connection.secret_key_decrypted,
            connection.testnet
        )
        
        # Step 1: Cancel the original order on exchange
        try:
            if original_order.exchange_order_id:
                await exchange_client.cancel_order(
                    symbol=original_order.symbol,
                    order_id=original_order.exchange_order_id
                )
                logger.info(f"Cancelled original order {original_order.id} on exchange")
        except Exception as e:
            logger.warning(f"Failed to cancel order on exchange: {e}")
            # Continue anyway - order might already be cancelled or filled
        
        # Update original order status in DB
        original_order.cancel("Replaced by modified order")
        await self._order_repository.update(original_order)
        
        # Step 2: Create new order with updated parameters
        new_order = original_order.clone_for_modification(
            new_quantity=new_quantity,
            new_price=new_price,
            new_stop_price=new_stop_price,
        )
        
        # Link to original order for traceability
        new_order.metadata = {
            **(new_order.metadata or {}),
            "replaces_order_id": str(original_order.id),
            "modification_reason": "cancel-and-replace"
        }
        
        # Save new order to DB first
        created_order = await self._order_repository.create(new_order)
        
        # Step 3: Submit new order to exchange
        try:
            order_params = created_order.to_exchange_params()
            exchange_result = await exchange_client.place_order(**order_params)
            
            # Update with exchange response
            created_order.submit(
                exchange_order_id=exchange_result['orderId'],
                client_order_id=exchange_result.get('clientOrderId')
            )
            
            await self._order_repository.update(created_order)
            
            logger.info(
                f"Order {original_order.id} modified -> new order {created_order.id} "
                f"(exchange_id: {exchange_result['orderId']})"
            )
            
            return created_order
            
        except Exception as e:
            # Mark new order as rejected
            created_order.reject(f"Exchange submission failed: {e}")
            await self._order_repository.update(created_order)
            
            logger.error(f"Failed to submit replacement order: {e}")
            raise ExchangeConnectionError(
                f"Original order cancelled but replacement failed: {e}. "
                f"Original order ID: {original_order.id}"
            )
