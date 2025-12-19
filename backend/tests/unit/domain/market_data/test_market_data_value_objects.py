"""Unit tests for Market Data domain value objects."""
import pytest
from datetime import datetime, timezone
from decimal import Decimal

from src.trading.domain.market_data import (
    DataType,
    CandleInterval,
    TradeType,
    StreamStatus,
    Tick,
    Candle,
    OrderBookLevel,
    OrderBook,
    Trade,
    FundingRate,
    MarketStats,
)


class TestDataType:
    """Test DataType enum."""
    
    def test_data_type_values(self):
        """Test that data type enum has correct values."""
        assert DataType.TICK == "TICK"
        assert DataType.CANDLE == "CANDLE"
        assert DataType.ORDER_BOOK == "ORDER_BOOK"
        assert DataType.TRADE == "TRADE"
        assert DataType.FUNDING_RATE == "FUNDING_RATE"
        assert DataType.MARK_PRICE == "MARK_PRICE"
    
    def test_data_type_enum_comparison(self):
        """Test data type enum comparison."""
        data_type = DataType.CANDLE
        assert data_type == DataType.CANDLE
        assert data_type != DataType.TICK
        assert data_type.value == "CANDLE"


class TestCandleInterval:
    """Test CandleInterval enum."""
    
    def test_candle_interval_values(self):
        """Test that candle interval enum has correct values."""
        assert CandleInterval.ONE_MINUTE == "1m"
        assert CandleInterval.THREE_MINUTE == "3m"
        assert CandleInterval.FIVE_MINUTE == "5m"
        assert CandleInterval.FIFTEEN_MINUTE == "15m"
        assert CandleInterval.THIRTY_MINUTE == "30m"
        assert CandleInterval.ONE_HOUR == "1h"
        assert CandleInterval.TWO_HOUR == "2h"
        assert CandleInterval.FOUR_HOUR == "4h"
        assert CandleInterval.SIX_HOUR == "6h"
        assert CandleInterval.EIGHT_HOUR == "8h"
        assert CandleInterval.TWELVE_HOUR == "12h"
        assert CandleInterval.ONE_DAY == "1d"
        assert CandleInterval.THREE_DAY == "3d"
        assert CandleInterval.ONE_WEEK == "1w"
        assert CandleInterval.ONE_MONTH == "1M"
    
    def test_candle_interval_enum_comparison(self):
        """Test candle interval enum comparison."""
        interval = CandleInterval.FIVE_MINUTE
        assert interval == CandleInterval.FIVE_MINUTE
        assert interval != CandleInterval.ONE_HOUR
        assert interval.value == "5m"


class TestTradeType:
    """Test TradeType enum."""
    
    def test_trade_type_values(self):
        """Test that trade type enum has correct values."""
        assert TradeType.BUY == "BUY"
        assert TradeType.SELL == "SELL"


class TestStreamStatus:
    """Test StreamStatus enum."""
    
    def test_stream_status_values(self):
        """Test that stream status enum has correct values."""
        assert StreamStatus.CONNECTING == "CONNECTING"
        assert StreamStatus.CONNECTED == "CONNECTED"
        assert StreamStatus.DISCONNECTED == "DISCONNECTED"
        assert StreamStatus.ERROR == "ERROR"
        assert StreamStatus.RECONNECTING == "RECONNECTING"


class TestTick:
    """Test Tick value object."""
    
    def test_valid_tick(self):
        """Test creating valid tick data."""
        timestamp = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        tick = Tick(
            symbol="BTCUSDT",
            price=Decimal("50000.50"),
            size=Decimal("0.5"),
            timestamp=timestamp,
            trade_id="12345",
            is_buyer_maker=True
        )
        
        assert tick.symbol == "BTCUSDT"
        assert tick.price == Decimal("50000.50")
        assert tick.size == Decimal("0.5")
        assert tick.timestamp == timestamp
        assert tick.trade_id == "12345"
        assert tick.is_buyer_maker is True
    
    def test_tick_minimal(self):
        """Test creating tick with minimal data."""
        timestamp = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        tick = Tick(
            symbol="ETHUSDT",
            price=Decimal("3500.00"),
            size=Decimal("1.0"),
            timestamp=timestamp
        )
        
        assert tick.trade_id is None
        assert tick.is_buyer_maker is None
    
    def test_invalid_tick_price(self):
        """Test that invalid price raises ValueError."""
        timestamp = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        with pytest.raises(ValueError, match="Price must be positive"):
            Tick(
                symbol="BTCUSDT",
                price=Decimal("0"),
                size=Decimal("0.5"),
                timestamp=timestamp
            )
        
        with pytest.raises(ValueError, match="Price must be positive"):
            Tick(
                symbol="BTCUSDT",
                price=Decimal("-100.50"),
                size=Decimal("0.5"),
                timestamp=timestamp
            )
    
    def test_invalid_tick_size(self):
        """Test that invalid size raises ValueError."""
        timestamp = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        with pytest.raises(ValueError, match="Size must be positive"):
            Tick(
                symbol="BTCUSDT",
                price=Decimal("50000.00"),
                size=Decimal("0"),
                timestamp=timestamp
            )
    
    def test_tick_immutability(self):
        """Test that Tick is immutable (frozen)."""
        timestamp = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        tick = Tick(
            symbol="BTCUSDT",
            price=Decimal("50000.00"),
            size=Decimal("0.5"),
            timestamp=timestamp
        )
        
        with pytest.raises(AttributeError):
            tick.price = Decimal("60000.00")


class TestCandle:
    """Test Candle value object."""
    
    def test_valid_candle(self):
        """Test creating valid candle data."""
        open_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        close_time = datetime(2024, 1, 1, 12, 5, 0, tzinfo=timezone.utc)
        
        candle = Candle(
            symbol="BTCUSDT",
            interval=CandleInterval.FIVE_MINUTE,
            open_price=Decimal("50000.00"),
            high_price=Decimal("51000.00"),
            low_price=Decimal("49500.00"),
            close_price=Decimal("50500.00"),
            volume=Decimal("100.5"),
            quote_volume=Decimal("5025000.00"),
            open_time=open_time,
            close_time=close_time,
            trade_count=500,
            taker_buy_volume=Decimal("60.0"),
            taker_buy_quote_volume=Decimal("3000000.00")
        )
        
        assert candle.symbol == "BTCUSDT"
        assert candle.interval == CandleInterval.FIVE_MINUTE
        assert candle.open_price == Decimal("50000.00")
        assert candle.high_price == Decimal("51000.00")
        assert candle.low_price == Decimal("49500.00")
        assert candle.close_price == Decimal("50500.00")
        assert candle.volume == Decimal("100.5")
        assert candle.quote_volume == Decimal("5025000.00")
        assert candle.trade_count == 500
    
    def test_candle_price_calculations(self):
        """Test candle price calculation properties."""
        open_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        close_time = datetime(2024, 1, 1, 12, 5, 0, tzinfo=timezone.utc)
        
        candle = Candle(
            symbol="BTCUSDT",
            interval=CandleInterval.FIVE_MINUTE,
            open_price=Decimal("50000.00"),
            high_price=Decimal("52000.00"),
            low_price=Decimal("48000.00"),
            close_price=Decimal("51000.00"),
            volume=Decimal("100.0"),
            quote_volume=Decimal("5000000.00"),
            open_time=open_time,
            close_time=close_time
        )
        
        # Price change: 51000 - 50000 = 1000
        assert candle.price_change == Decimal("1000.00")
        
        # Price change percent: (1000 / 50000) * 100 = 2%
        assert candle.price_change_percent == Decimal("2.0")
        
        # Typical price: (52000 + 48000 + 51000) / 3 = 50333.33...
        expected_typical = (Decimal("52000") + Decimal("48000") + Decimal("51000")) / 3
        assert candle.typical_price == expected_typical
        
        # Weighted price: 5000000 / 100 = 50000
        assert candle.weighted_price == Decimal("50000.00")
    
    def test_candle_weighted_price_zero_volume(self):
        """Test weighted price when volume is zero."""
        open_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        close_time = datetime(2024, 1, 1, 12, 5, 0, tzinfo=timezone.utc)
        
        candle = Candle(
            symbol="BTCUSDT",
            interval=CandleInterval.FIVE_MINUTE,
            open_price=Decimal("50000.00"),
            high_price=Decimal("52000.00"),
            low_price=Decimal("48000.00"),
            close_price=Decimal("51000.00"),
            volume=Decimal("0"),
            quote_volume=Decimal("0"),
            open_time=open_time,
            close_time=close_time
        )
        
        # Should fallback to typical price when volume is zero
        assert candle.weighted_price == candle.typical_price
    
    def test_invalid_candle_prices(self):
        """Test that invalid prices raise ValueError."""
        open_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        close_time = datetime(2024, 1, 1, 12, 5, 0, tzinfo=timezone.utc)
        
        # Test zero open price
        with pytest.raises(ValueError, match="Open price must be positive"):
            Candle(
                symbol="BTCUSDT",
                interval=CandleInterval.FIVE_MINUTE,
                open_price=Decimal("0"),
                high_price=Decimal("51000.00"),
                low_price=Decimal("49500.00"),
                close_price=Decimal("50500.00"),
                volume=Decimal("100.0"),
                quote_volume=Decimal("5000000.00"),
                open_time=open_time,
                close_time=close_time
            )
    
    def test_invalid_candle_volumes(self):
        """Test that negative volumes raise ValueError."""
        open_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        close_time = datetime(2024, 1, 1, 12, 5, 0, tzinfo=timezone.utc)
        
        with pytest.raises(ValueError, match="Volume cannot be negative"):
            Candle(
                symbol="BTCUSDT",
                interval=CandleInterval.FIVE_MINUTE,
                open_price=Decimal("50000.00"),
                high_price=Decimal("51000.00"),
                low_price=Decimal("49500.00"),
                close_price=Decimal("50500.00"),
                volume=Decimal("-10.0"),
                quote_volume=Decimal("5000000.00"),
                open_time=open_time,
                close_time=close_time
            )
    
    def test_invalid_candle_time_range(self):
        """Test that invalid time range raises ValueError."""
        open_time = datetime(2024, 1, 1, 12, 5, 0, tzinfo=timezone.utc)
        close_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)  # Before open time
        
        with pytest.raises(ValueError, match="Open time must be before close time"):
            Candle(
                symbol="BTCUSDT",
                interval=CandleInterval.FIVE_MINUTE,
                open_price=Decimal("50000.00"),
                high_price=Decimal("51000.00"),
                low_price=Decimal("49500.00"),
                close_price=Decimal("50500.00"),
                volume=Decimal("100.0"),
                quote_volume=Decimal("5000000.00"),
                open_time=open_time,
                close_time=close_time
            )
    
    def test_invalid_price_relationships(self):
        """Test that invalid price relationships raise ValueError."""
        open_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        close_time = datetime(2024, 1, 1, 12, 5, 0, tzinfo=timezone.utc)
        
        # Open price above high
        with pytest.raises(ValueError, match="Open price must be between low and high"):
            Candle(
                symbol="BTCUSDT",
                interval=CandleInterval.FIVE_MINUTE,
                open_price=Decimal("52000.00"),  # Above high
                high_price=Decimal("51000.00"),
                low_price=Decimal("49500.00"),
                close_price=Decimal("50500.00"),
                volume=Decimal("100.0"),
                quote_volume=Decimal("5000000.00"),
                open_time=open_time,
                close_time=close_time
            )
        
        # Close price below low
        with pytest.raises(ValueError, match="Close price must be between low and high"):
            Candle(
                symbol="BTCUSDT",
                interval=CandleInterval.FIVE_MINUTE,
                open_price=Decimal("50000.00"),
                high_price=Decimal("51000.00"),
                low_price=Decimal("49500.00"),
                close_price=Decimal("49000.00"),  # Below low
                volume=Decimal("100.0"),
                quote_volume=Decimal("5000000.00"),
                open_time=open_time,
                close_time=close_time
            )
    
    def test_candle_immutability(self):
        """Test that Candle is immutable (frozen)."""
        open_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        close_time = datetime(2024, 1, 1, 12, 5, 0, tzinfo=timezone.utc)
        
        candle = Candle(
            symbol="BTCUSDT",
            interval=CandleInterval.FIVE_MINUTE,
            open_price=Decimal("50000.00"),
            high_price=Decimal("51000.00"),
            low_price=Decimal("49500.00"),
            close_price=Decimal("50500.00"),
            volume=Decimal("100.0"),
            quote_volume=Decimal("5000000.00"),
            open_time=open_time,
            close_time=close_time
        )
        
        with pytest.raises(AttributeError):
            candle.close_price = Decimal("52000.00")


class TestOrderBookLevel:
    """Test OrderBookLevel value object."""
    
    def test_valid_order_book_level(self):
        """Test creating valid order book level."""
        level = OrderBookLevel(
            price=Decimal("50000.00"),
            quantity=Decimal("1.5")
        )
        
        assert level.price == Decimal("50000.00")
        assert level.quantity == Decimal("1.5")
    
    def test_zero_quantity_order_book_level(self):
        """Test creating order book level with zero quantity."""
        level = OrderBookLevel(
            price=Decimal("50000.00"),
            quantity=Decimal("0")  # Zero quantity is allowed
        )
        
        assert level.quantity == Decimal("0")
    
    def test_invalid_order_book_level_price(self):
        """Test that invalid price raises ValueError."""
        with pytest.raises(ValueError, match="Price must be positive"):
            OrderBookLevel(
                price=Decimal("0"),
                quantity=Decimal("1.5")
            )
    
    def test_invalid_order_book_level_quantity(self):
        """Test that negative quantity raises ValueError."""
        with pytest.raises(ValueError, match="Quantity cannot be negative"):
            OrderBookLevel(
                price=Decimal("50000.00"),
                quantity=Decimal("-1.5")
            )
    
    def test_order_book_level_immutability(self):
        """Test that OrderBookLevel is immutable (frozen)."""
        level = OrderBookLevel(
            price=Decimal("50000.00"),
            quantity=Decimal("1.5")
        )
        
        with pytest.raises(AttributeError):
            level.price = Decimal("60000.00")