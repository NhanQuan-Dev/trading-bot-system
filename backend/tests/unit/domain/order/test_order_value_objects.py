"""Unit tests for Order domain value objects."""
import pytest
from decimal import Decimal

from src.trading.domain.order import (
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


class TestOrderSide:
    """Test OrderSide enum."""
    
    def test_order_side_values(self):
        """Test that order side enum has correct values."""
        assert OrderSide.BUY == "BUY"
        assert OrderSide.SELL == "SELL"
    
    def test_order_side_enum_comparison(self):
        """Test order side enum comparison."""
        side = OrderSide.BUY
        assert side == OrderSide.BUY
        assert side != OrderSide.SELL
        assert side.value == "BUY"


class TestOrderType:
    """Test OrderType enum."""
    
    def test_order_type_values(self):
        """Test that order type enum has correct values."""
        assert OrderType.MARKET == "MARKET"
        assert OrderType.LIMIT == "LIMIT"
        assert OrderType.STOP == "STOP"
        assert OrderType.STOP_MARKET == "STOP_MARKET"
        assert OrderType.TAKE_PROFIT == "TAKE_PROFIT"
        assert OrderType.TAKE_PROFIT_MARKET == "TAKE_PROFIT_MARKET"
        assert OrderType.TRAILING_STOP_MARKET == "TRAILING_STOP_MARKET"
    
    def test_order_type_enum_comparison(self):
        """Test order type enum comparison."""
        order_type = OrderType.LIMIT
        assert order_type == OrderType.LIMIT
        assert order_type != OrderType.MARKET
        assert order_type.value == "LIMIT"


class TestTimeInForce:
    """Test TimeInForce enum."""
    
    def test_time_in_force_values(self):
        """Test that time in force enum has correct values."""
        assert TimeInForce.GTC == "GTC"
        assert TimeInForce.IOC == "IOC"
        assert TimeInForce.FOK == "FOK"
        assert TimeInForce.GTX == "GTX"


class TestOrderStatus:
    """Test OrderStatus enum."""
    
    def test_order_status_values(self):
        """Test that order status enum has correct values."""
        assert OrderStatus.PENDING == "PENDING"
        assert OrderStatus.NEW == "NEW"
        assert OrderStatus.PARTIALLY_FILLED == "PARTIALLY_FILLED"
        assert OrderStatus.FILLED == "FILLED"
        assert OrderStatus.CANCELLED == "CANCELLED"
        assert OrderStatus.REJECTED == "REJECTED"
        assert OrderStatus.EXPIRED == "EXPIRED"


class TestPositionSide:
    """Test PositionSide enum."""
    
    def test_position_side_values(self):
        """Test that position side enum has correct values."""
        assert PositionSide.BOTH == "BOTH"
        assert PositionSide.LONG == "LONG"
        assert PositionSide.SHORT == "SHORT"


class TestWorkingType:
    """Test WorkingType enum."""
    
    def test_working_type_values(self):
        """Test that working type enum has correct values."""
        assert WorkingType.MARK_PRICE == "MARK_PRICE"
        assert WorkingType.CONTRACT_PRICE == "CONTRACT_PRICE"


class TestOrderPrice:
    """Test OrderPrice value object."""
    
    def test_valid_order_price(self):
        """Test creating valid order price."""
        price = OrderPrice(Decimal("50000.50"))
        assert price.value == Decimal("50000.50")
    
    def test_order_price_formatting(self):
        """Test order price formatting for exchange API."""
        # Test with decimal places
        price = OrderPrice(Decimal("50000.12345678"))
        assert price.formatted == "50000.12345678"
        
        # Test with trailing zeros
        price = OrderPrice(Decimal("50000.10000000"))
        assert price.formatted == "50000.1"
        
        # Test whole number
        price = OrderPrice(Decimal("50000.00000000"))
        assert price.formatted == "50000"
        
        # Test small decimal
        price = OrderPrice(Decimal("0.00000123"))
        assert price.formatted == "0.00000123"
    
    def test_invalid_order_price_zero(self):
        """Test that zero price raises ValueError."""
        with pytest.raises(ValueError, match="Order price must be positive"):
            OrderPrice(Decimal("0"))
    
    def test_invalid_order_price_negative(self):
        """Test that negative price raises ValueError."""
        with pytest.raises(ValueError, match="Order price must be positive"):
            OrderPrice(Decimal("-100.50"))
    
    def test_order_price_immutability(self):
        """Test that OrderPrice is immutable (frozen)."""
        price = OrderPrice(Decimal("100.50"))
        
        with pytest.raises(AttributeError):
            price.value = Decimal("200.50")


class TestOrderQuantity:
    """Test OrderQuantity value object."""
    
    def test_valid_order_quantity(self):
        """Test creating valid order quantity."""
        quantity = OrderQuantity(Decimal("1.5"))
        assert quantity.value == Decimal("1.5")
    
    def test_order_quantity_formatting(self):
        """Test order quantity formatting for exchange API."""
        # Test with decimal places
        quantity = OrderQuantity(Decimal("1.12345678"))
        assert quantity.formatted == "1.12345678"
        
        # Test with trailing zeros
        quantity = OrderQuantity(Decimal("1.50000000"))
        assert quantity.formatted == "1.5"
        
        # Test whole number
        quantity = OrderQuantity(Decimal("10.00000000"))
        assert quantity.formatted == "10"
        
        # Test small decimal
        quantity = OrderQuantity(Decimal("0.00000123"))
        assert quantity.formatted == "0.00000123"
    
    def test_invalid_order_quantity_zero(self):
        """Test that zero quantity raises ValueError."""
        with pytest.raises(ValueError, match="Order quantity must be positive"):
            OrderQuantity(Decimal("0"))
    
    def test_invalid_order_quantity_negative(self):
        """Test that negative quantity raises ValueError."""
        with pytest.raises(ValueError, match="Order quantity must be positive"):
            OrderQuantity(Decimal("-1.5"))
    
    def test_order_quantity_immutability(self):
        """Test that OrderQuantity is immutable (frozen)."""
        quantity = OrderQuantity(Decimal("1.5"))
        
        with pytest.raises(AttributeError):
            quantity.value = Decimal("2.5")


class TestOrderExecution:
    """Test OrderExecution value object."""
    
    def test_default_order_execution(self):
        """Test creating order execution with default values."""
        execution = OrderExecution()
        
        assert execution.executed_quantity == Decimal("0")
        assert execution.executed_quote == Decimal("0")
        assert execution.avg_price is None
        assert execution.commission == Decimal("0")
        assert execution.commission_asset == "USDT"
    
    def test_order_execution_with_values(self):
        """Test creating order execution with specific values."""
        execution = OrderExecution(
            executed_quantity=Decimal("1.5"),
            executed_quote=Decimal("75000.75"),
            avg_price=Decimal("50000.50"),
            commission=Decimal("37.50"),
            commission_asset="BNB"
        )
        
        assert execution.executed_quantity == Decimal("1.5")
        assert execution.executed_quote == Decimal("75000.75")
        assert execution.avg_price == Decimal("50000.50")
        assert execution.commission == Decimal("37.50")
        assert execution.commission_asset == "BNB"
    
    def test_remaining_quantity_property(self):
        """Test remaining quantity property (simplified)."""
        execution = OrderExecution(executed_quantity=Decimal("0.5"))
        # Note: This is simplified, actual calculation requires original quantity
        assert execution.remaining_quantity == Decimal("0")
    
    def test_fill_percentage_property(self):
        """Test fill percentage property (simplified)."""
        execution = OrderExecution(executed_quantity=Decimal("0.5"))
        # Note: This is simplified, actual calculation requires original quantity
        assert execution.fill_percentage == 0.0
    
    def test_order_execution_immutability(self):
        """Test that OrderExecution is immutable (frozen)."""
        execution = OrderExecution(executed_quantity=Decimal("1.0"))
        
        with pytest.raises(AttributeError):
            execution.executed_quantity = Decimal("2.0")