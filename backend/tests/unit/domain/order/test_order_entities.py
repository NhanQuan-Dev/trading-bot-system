"""Unit tests for Order domain entities."""
import pytest
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch

from src.trading.domain.order import (
    Order,
    OrderSide,
    OrderType,
    TimeInForce,
    OrderStatus,
    PositionSide,
    WorkingType,
    OrderPrice,
    OrderQuantity,
    OrderExecution,
)


class TestOrder:
    """Test Order entity."""
    
    def test_create_market_order(self):
        """Test creating a market order."""
        user_id = uuid.uuid4()
        exchange_connection_id = uuid.uuid4()
        bot_id = uuid.uuid4()
        quantity = Decimal("1.5")
        
        with patch('src.trading.domain.order.dt') as mock_dt:
            mock_now = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
            mock_dt.now.return_value = mock_now
            mock_dt.timezone.utc = timezone.utc
            
            order = Order.create_market_order(
                user_id=user_id,
                exchange_connection_id=exchange_connection_id,
                symbol="BTCUSDT",
                side=OrderSide.BUY,
                quantity=quantity,
                bot_id=bot_id,
                position_side=PositionSide.LONG,
                reduce_only=True,
                leverage=10
            )
        
        assert isinstance(order.id, uuid.UUID)
        assert order.user_id == user_id
        assert order.bot_id == bot_id
        assert order.exchange_connection_id == exchange_connection_id
        assert order.symbol == "BTCUSDT"
        assert order.side == OrderSide.BUY
        assert order.order_type == OrderType.MARKET
        assert order.quantity.value == quantity
        assert order.position_side == PositionSide.LONG
        assert order.reduce_only is True
        assert order.leverage == 10
        assert order.status == OrderStatus.PENDING
        assert order.created_at == mock_now
        assert order.updated_at == mock_now
        assert order.price is None
        assert order.stop_price is None
        assert isinstance(order.execution, OrderExecution)
        assert order.meta_data == {}
    
    def test_create_market_order_minimal(self):
        """Test creating market order with minimal parameters."""
        order = Order.create_market_order(
            user_id=uuid.uuid4(),
            exchange_connection_id=uuid.uuid4(),
            symbol="ETHUSDT",
            side=OrderSide.SELL,
            quantity=Decimal("2.0")
        )
        
        assert order.bot_id is None
        assert order.position_side == PositionSide.BOTH  # Default
        assert order.reduce_only is False  # Default
        assert order.leverage == 1  # Default
        assert order.order_type == OrderType.MARKET
        assert order.status == OrderStatus.PENDING
    
    def test_create_limit_order(self):
        """Test creating a limit order."""
        user_id = uuid.uuid4()
        exchange_connection_id = uuid.uuid4()
        quantity = Decimal("0.001")
        price = Decimal("50000.50")
        
        with patch('src.trading.domain.order.dt') as mock_dt:
            mock_now = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
            mock_dt.now.return_value = mock_now
            mock_dt.timezone.utc = timezone.utc
            
            order = Order.create_limit_order(
                user_id=user_id,
                exchange_connection_id=exchange_connection_id,
                symbol="BTCUSDT",
                side=OrderSide.BUY,
                quantity=quantity,
                price=price,
                time_in_force=TimeInForce.IOC,
                reduce_only=False,
                leverage=5
            )
        
        assert order.order_type == OrderType.LIMIT
        assert order.quantity.value == quantity
        assert order.price.value == price
        assert order.time_in_force == TimeInForce.IOC
        assert order.reduce_only is False
        assert order.leverage == 5
        assert order.status == OrderStatus.PENDING
        assert order.stop_price is None
    
    def test_create_limit_order_minimal(self):
        """Test creating limit order with minimal parameters."""
        order = Order.create_limit_order(
            user_id=uuid.uuid4(),
            exchange_connection_id=uuid.uuid4(),
            symbol="ADAUSDT",
            side=OrderSide.SELL,
            quantity=Decimal("1000"),
            price=Decimal("0.45")
        )
        
        assert order.bot_id is None
        assert order.position_side == PositionSide.BOTH  # Default
        assert order.time_in_force == TimeInForce.GTC  # Default
        assert order.reduce_only is False  # Default
        assert order.leverage == 1  # Default
    
    def test_create_stop_market_order(self):
        """Test creating a stop market order."""
        user_id = uuid.uuid4()
        exchange_connection_id = uuid.uuid4()
        quantity = Decimal("0.5")
        stop_price = Decimal("48000.00")
        
        with patch('src.trading.domain.order.dt') as mock_dt:
            mock_now = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
            mock_dt.now.return_value = mock_now
            mock_dt.timezone.utc = timezone.utc
            
            order = Order.create_stop_market_order(
                user_id=user_id,
                exchange_connection_id=exchange_connection_id,
                symbol="BTCUSDT",
                side=OrderSide.SELL,
                quantity=quantity,
                stop_price=stop_price,
                working_type=WorkingType.MARK_PRICE,
                reduce_only=True,
                leverage=20
            )
        
        assert order.order_type == OrderType.STOP_MARKET
        assert order.quantity.value == quantity
        assert order.stop_price.value == stop_price
        assert order.working_type == WorkingType.MARK_PRICE
        assert order.reduce_only is True
        assert order.leverage == 20
        assert order.price is None
    
    def test_submit_order(self):
        """Test submitting order to exchange."""
        order = Order.create_market_order(
            user_id=uuid.uuid4(),
            exchange_connection_id=uuid.uuid4(),
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            quantity=Decimal("1.0")
        )
        
        exchange_order_id = "12345678"
        client_order_id = "client_12345"
        
        with patch('src.trading.domain.order.dt') as mock_dt:
            mock_now = datetime(2024, 1, 1, 12, 30, 0, tzinfo=timezone.utc)
            mock_dt.now.return_value = mock_now
            mock_dt.timezone.utc = timezone.utc
            
            order.submit(exchange_order_id, client_order_id)
        
        assert order.status == OrderStatus.NEW
        assert order.exchange_order_id == exchange_order_id
        assert order.client_order_id == client_order_id
        assert order.submitted_at == mock_now
        assert order.updated_at == mock_now
    
    def test_submit_order_without_client_id(self):
        """Test submitting order without client order ID."""
        order = Order.create_market_order(
            user_id=uuid.uuid4(),
            exchange_connection_id=uuid.uuid4(),
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            quantity=Decimal("1.0")
        )
        
        order.submit("exchange_123")
        
        assert order.status == OrderStatus.NEW
        assert order.exchange_order_id == "exchange_123"
        assert order.client_order_id is None
    
    def test_fill_order_completely(self):
        """Test completely filling an order."""
        order = Order.create_market_order(
            user_id=uuid.uuid4(),
            exchange_connection_id=uuid.uuid4(),
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            quantity=Decimal("1.0")
        )
        
        order.submit("12345678")
        
        executed_quantity = Decimal("1.0")
        executed_price = Decimal("50000.00")
        commission = Decimal("25.00")
        
        with patch('src.trading.domain.order.dt') as mock_dt:
            mock_now = datetime(2024, 1, 1, 13, 0, 0, tzinfo=timezone.utc)
            mock_dt.now.return_value = mock_now
            mock_dt.timezone.utc = timezone.utc
            
            order.fill(executed_quantity, executed_price, commission, "USDT")
        
        assert order.status == OrderStatus.FILLED
        assert order.execution.executed_quantity == executed_quantity
        assert order.execution.executed_quote == Decimal("50000.00")
        assert order.execution.avg_price == executed_price
        assert order.execution.commission == commission
        assert order.execution.commission_asset == "USDT"
        assert order.filled_at == mock_now
        assert order.updated_at == mock_now
    
    def test_fill_order_partially(self):
        """Test partially filling an order."""
        order = Order.create_limit_order(
            user_id=uuid.uuid4(),
            exchange_connection_id=uuid.uuid4(),
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            quantity=Decimal("2.0"),
            price=Decimal("50000.00")
        )
        
        order.submit("12345678")
        
        # First partial fill
        order.fill(Decimal("0.5"), Decimal("49900.00"), Decimal("12.475"))
        
        assert order.status == OrderStatus.PARTIALLY_FILLED
        assert order.execution.executed_quantity == Decimal("0.5")
        assert order.execution.executed_quote == Decimal("24950.00")
        assert order.execution.avg_price == Decimal("49900.00")
        assert order.execution.commission == Decimal("12.475")
        assert order.filled_at is None  # Only set when completely filled
        
        # Second partial fill
        order.fill(Decimal("1.0"), Decimal("50100.00"), Decimal("25.05"))
        
        assert order.status == OrderStatus.PARTIALLY_FILLED
        assert order.execution.executed_quantity == Decimal("1.5")
        assert order.execution.executed_quote == Decimal("75050.00")  # 24950 + 50100
        # Average price calculation: 75050 / 1.5 = 50033.33...
        expected_avg_price = Decimal("75050.00") / Decimal("1.5")
        assert order.execution.avg_price == expected_avg_price
        assert order.execution.commission == Decimal("37.525")  # 12.475 + 25.05
        
        # Final fill
        order.fill(Decimal("0.5"), Decimal("50200.00"), Decimal("12.55"))
        
        assert order.status == OrderStatus.FILLED
        assert order.execution.executed_quantity == Decimal("2.0")
        assert order.execution.executed_quote == Decimal("100150.00")  # 75050 + 25100
        assert order.execution.commission == Decimal("50.075")  # 37.525 + 12.55
        assert order.filled_at is not None
    
    def test_cancel_order(self):
        """Test cancelling an order."""
        order = Order.create_limit_order(
            user_id=uuid.uuid4(),
            exchange_connection_id=uuid.uuid4(),
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            quantity=Decimal("1.0"),
            price=Decimal("50000.00")
        )
        
        order.submit("12345678")
        
        with patch('src.trading.domain.order.dt') as mock_dt:
            mock_now = datetime(2024, 1, 1, 14, 0, 0, tzinfo=timezone.utc)
            mock_dt.now.return_value = mock_now
            mock_dt.timezone.utc = timezone.utc
            
            order.cancel("User cancelled")
        
        assert order.status == OrderStatus.CANCELLED
        assert order.cancelled_at == mock_now
        assert order.updated_at == mock_now
        assert order.error_message == "User cancelled"
    
    def test_cancel_order_without_reason(self):
        """Test cancelling order without reason."""
        order = Order.create_limit_order(
            user_id=uuid.uuid4(),
            exchange_connection_id=uuid.uuid4(),
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            quantity=Decimal("1.0"),
            price=Decimal("50000.00")
        )
        
        order.submit("12345678")
        order.cancel()
        
        assert order.status == OrderStatus.CANCELLED
        assert order.error_message is None
    
    def test_cancel_filled_order_raises_error(self):
        """Test that cancelling filled order raises error."""
        order = Order.create_market_order(
            user_id=uuid.uuid4(),
            exchange_connection_id=uuid.uuid4(),
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            quantity=Decimal("1.0")
        )
        
        order.submit("12345678")
        order.fill(Decimal("1.0"), Decimal("50000.00"))
        assert order.status == OrderStatus.FILLED
        
        with pytest.raises(ValueError, match="Cannot cancel order in OrderStatus.FILLED status"):
            order.cancel()
    
    def test_cancel_already_cancelled_order_raises_error(self):
        """Test that cancelling already cancelled order raises error."""
        order = Order.create_limit_order(
            user_id=uuid.uuid4(),
            exchange_connection_id=uuid.uuid4(),
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            quantity=Decimal("1.0"),
            price=Decimal("50000.00")
        )
        
        order.submit("12345678")
        order.cancel()
        assert order.status == OrderStatus.CANCELLED
        
        with pytest.raises(ValueError, match="Cannot cancel order in OrderStatus.CANCELLED status"):
            order.cancel()
    
    def test_reject_order(self):
        """Test rejecting an order."""
        order = Order.create_market_order(
            user_id=uuid.uuid4(),
            exchange_connection_id=uuid.uuid4(),
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            quantity=Decimal("1.0")
        )
        
        with patch('src.trading.domain.order.dt') as mock_dt:
            mock_now = datetime(2024, 1, 1, 15, 0, 0, tzinfo=timezone.utc)
            mock_dt.now.return_value = mock_now
            mock_dt.timezone.utc = timezone.utc
            
            order.reject("Insufficient balance")
        
        assert order.status == OrderStatus.REJECTED
        assert order.error_message == "Insufficient balance"
        assert order.updated_at == mock_now
    
    def test_order_status_checks(self):
        """Test order status check methods."""
        order = Order.create_limit_order(
            user_id=uuid.uuid4(),
            exchange_connection_id=uuid.uuid4(),
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            quantity=Decimal("1.0"),
            price=Decimal("50000.00")
        )
        
        # Pending order
        assert order.is_active() is True
        assert order.is_filled() is False
        
        # Submitted order
        order.submit("12345678")
        assert order.is_active() is True
        assert order.is_filled() is False
        
        # Partially filled order
        order.fill(Decimal("0.5"), Decimal("50000.00"))
        assert order.is_active() is True
        assert order.is_filled() is False
        
        # Completely filled order
        order.fill(Decimal("0.5"), Decimal("50000.00"))
        assert order.is_active() is False
        assert order.is_filled() is True
    
    def test_get_remaining_quantity(self):
        """Test getting remaining quantity."""
        order = Order.create_limit_order(
            user_id=uuid.uuid4(),
            exchange_connection_id=uuid.uuid4(),
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            quantity=Decimal("2.0"),
            price=Decimal("50000.00")
        )
        
        # No execution
        assert order.get_remaining_quantity() == Decimal("2.0")
        
        # Partial execution
        order.submit("12345678")
        order.fill(Decimal("0.7"), Decimal("50000.00"))
        assert order.get_remaining_quantity() == Decimal("1.3")
        
        # Full execution
        order.fill(Decimal("1.3"), Decimal("50000.00"))
        assert order.get_remaining_quantity() == Decimal("0")
    
    def test_get_fill_percentage(self):
        """Test getting fill percentage."""
        order = Order.create_limit_order(
            user_id=uuid.uuid4(),
            exchange_connection_id=uuid.uuid4(),
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            quantity=Decimal("2.0"),
            price=Decimal("50000.00")
        )
        
        # No execution
        assert order.get_fill_percentage() == 0.0
        
        # Partial execution
        order.submit("12345678")
        order.fill(Decimal("0.5"), Decimal("50000.00"))
        assert order.get_fill_percentage() == 25.0
        
        # More partial execution
        order.fill(Decimal("1.0"), Decimal("50000.00"))
        assert order.get_fill_percentage() == 75.0
        
        # Full execution
        order.fill(Decimal("0.5"), Decimal("50000.00"))
        assert order.get_fill_percentage() == 100.0
    
    def test_to_exchange_params_market_order(self):
        """Test converting market order to exchange parameters."""
        order = Order.create_market_order(
            user_id=uuid.uuid4(),
            exchange_connection_id=uuid.uuid4(),
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            quantity=Decimal("1.5"),
            position_side=PositionSide.LONG,
            reduce_only=True
        )
        
        params = order.to_exchange_params()
        
        expected_params = {
            "symbol": "BTCUSDT",
            "side": "BUY",
            "type": "MARKET",
            "quantity": "1.5",
            "positionSide": "LONG",
            "reduceOnly": "true"
        }
        
        assert params == expected_params
    
    def test_to_exchange_params_limit_order(self):
        """Test converting limit order to exchange parameters."""
        order = Order.create_limit_order(
            user_id=uuid.uuid4(),
            exchange_connection_id=uuid.uuid4(),
            symbol="ETHUSDT",
            side=OrderSide.SELL,
            quantity=Decimal("2.5"),
            price=Decimal("3500.50"),
            time_in_force=TimeInForce.IOC,
            reduce_only=False
        )
        
        order.client_order_id = "client_12345"
        
        params = order.to_exchange_params()
        
        expected_params = {
            "symbol": "ETHUSDT",
            "side": "SELL",
            "type": "LIMIT",
            "quantity": "2.5",
            "price": "3500.5",
            "timeInForce": "IOC",
            "positionSide": "BOTH",
            "reduceOnly": "false",
            "newClientOrderId": "client_12345"
        }
        
        assert params == expected_params
    
    def test_to_exchange_params_stop_market_order(self):
        """Test converting stop market order to exchange parameters."""
        order = Order.create_stop_market_order(
            user_id=uuid.uuid4(),
            exchange_connection_id=uuid.uuid4(),
            symbol="BTCUSDT",
            side=OrderSide.SELL,
            quantity=Decimal("0.001"),
            stop_price=Decimal("48000.00"),
            working_type=WorkingType.MARK_PRICE,
            reduce_only=True
        )
        
        params = order.to_exchange_params()
        
        expected_params = {
            "symbol": "BTCUSDT",
            "side": "SELL",
            "type": "STOP_MARKET",
            "quantity": "0.001",
            "stopPrice": "48000",
            "workingType": "MARK_PRICE",
            "positionSide": "BOTH",
            "reduceOnly": "true"
        }
        
        assert params == expected_params
    
    def test_to_exchange_params_with_optional_fields(self):
        """Test converting order with optional fields to exchange parameters."""
        order = Order.create_market_order(
            user_id=uuid.uuid4(),
            exchange_connection_id=uuid.uuid4(),
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            quantity=Decimal("1.0")
        )
        
        # Set optional fields
        order.callback_rate = Decimal("0.1")  # For trailing stop
        order.close_position = True
        order.price_protect = True
        order.client_order_id = "test_client_123"
        
        params = order.to_exchange_params()
        
        assert params["callbackRate"] == "0.1000"
        assert params["closePosition"] == "true"
        assert params["priceProtect"] == "true"
        assert params["newClientOrderId"] == "test_client_123"