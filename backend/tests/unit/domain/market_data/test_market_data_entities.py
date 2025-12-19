"""Test cases for Market Data entities."""
import pytest
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch
import uuid

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
    MarketDataSubscription
)


class TestOrderBook:
    """Test OrderBook entity."""

    def test_valid_order_book(self):
        """Test creating valid order book."""
        timestamp = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        bids = [
            OrderBookLevel(Decimal("50000.00"), Decimal("1.0")),
            OrderBookLevel(Decimal("49999.00"), Decimal("2.0")),
        ]
        
        asks = [
            OrderBookLevel(Decimal("50001.00"), Decimal("0.5")),
            OrderBookLevel(Decimal("50002.00"), Decimal("1.0")),
        ]
        
        order_book = OrderBook(
            symbol="BTCUSDT",
            bids=bids,
            asks=asks,
            timestamp=timestamp
        )
        
        assert order_book.symbol == "BTCUSDT"
        assert order_book.bids == bids
        assert order_book.asks == asks
        assert order_book.timestamp == timestamp

    def test_best_bid_ask(self):
        """Test best bid and ask calculation."""
        timestamp = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        bids = [
            OrderBookLevel(Decimal("50000.00"), Decimal("1.0")),
            OrderBookLevel(Decimal("49999.00"), Decimal("2.0")),
        ]
        
        asks = [
            OrderBookLevel(Decimal("50001.00"), Decimal("0.5")),
            OrderBookLevel(Decimal("50002.00"), Decimal("1.0")),
        ]
        
        order_book = OrderBook(
            symbol="BTCUSDT",
            bids=bids,
            asks=asks,
            timestamp=timestamp
        )
        
        assert order_book.best_bid_price == Decimal("50000.00")
        assert order_book.best_ask_price == Decimal("50001.00")

    def test_spread_calculation(self):
        """Test spread calculation."""
        timestamp = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        bids = [OrderBookLevel(Decimal("50000.00"), Decimal("1.0"))]
        asks = [OrderBookLevel(Decimal("50001.00"), Decimal("0.5"))]
        
        order_book = OrderBook(
            symbol="BTCUSDT",
            bids=bids,
            asks=asks,
            timestamp=timestamp
        )
        
        assert order_book.spread == Decimal("1.00")
        
        # Calculate expected spread percentage: (spread / mid_price) * 100
        # mid_price = (50000 + 50001) / 2 = 50000.5
        # spread_percent = (1.00 / 50000.5) * 100
        expected_spread_percent = (Decimal("1.00") / Decimal("50000.5")) * 100
        assert order_book.spread_percent == expected_spread_percent

    def test_order_book_depth_calculations(self):
        """Test order book depth calculations."""
        timestamp = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        bids = [
            OrderBookLevel(Decimal("50000.00"), Decimal("1.0")),
            OrderBookLevel(Decimal("49999.00"), Decimal("2.0")),
            OrderBookLevel(Decimal("49998.00"), Decimal("1.5")),
        ]
        
        asks = [
            OrderBookLevel(Decimal("50001.00"), Decimal("0.5")),
            OrderBookLevel(Decimal("50002.00"), Decimal("1.0")),
            OrderBookLevel(Decimal("50003.00"), Decimal("2.0")),
        ]
        
        order_book = OrderBook(
            symbol="BTCUSDT",
            bids=bids,
            asks=asks,
            timestamp=timestamp
        )
        
        # Bid depth at or above 49999: 1.0 + 2.0 = 3.0
        assert order_book.get_bid_depth(Decimal("49999.00")) == Decimal("3.0")
        
        # Bid depth at or above 50000: 1.0
        assert order_book.get_bid_depth(Decimal("50000.00")) == Decimal("1.0")
        
        # Ask depth at or below 50002: 0.5 + 1.0 = 1.5
        assert order_book.get_ask_depth(Decimal("50002.00")) == Decimal("1.5")
        
        # Ask depth at or below 50001: 0.5
        assert order_book.get_ask_depth(Decimal("50001.00")) == Decimal("0.5")

    def test_invalid_bid_ordering(self):
        """Test that invalid bid ordering raises ValueError."""
        timestamp = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        # Bids not sorted by price descending
        bids = [
            OrderBookLevel(Decimal("49999.00"), Decimal("1.0")),
            OrderBookLevel(Decimal("50000.00"), Decimal("2.0")),  # Higher price after lower
        ]
        
        asks = [OrderBookLevel(Decimal("50001.00"), Decimal("0.5"))]
        
        with pytest.raises(ValueError, match="Bids must be sorted by price descending"):
            OrderBook(
                symbol="BTCUSDT",
                bids=bids,
                asks=asks,
                timestamp=timestamp
            )

    def test_invalid_ask_ordering(self):
        """Test that invalid ask ordering raises ValueError."""
        timestamp = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        bids = [OrderBookLevel(Decimal("50000.00"), Decimal("1.0"))]
        
        # Asks not sorted by price ascending
        asks = [
            OrderBookLevel(Decimal("50002.00"), Decimal("1.0")),
            OrderBookLevel(Decimal("50001.00"), Decimal("0.5")),  # Lower price after higher
        ]
        
        with pytest.raises(ValueError, match="Asks must be sorted by price ascending"):
            OrderBook(
                symbol="BTCUSDT",
                bids=bids,
                asks=asks,
                timestamp=timestamp
            )

    def test_invalid_spread(self):
        """Test that invalid spread (bid >= ask) raises ValueError."""
        timestamp = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        bids = [OrderBookLevel(Decimal("50001.00"), Decimal("1.0"))]  # Higher than ask
        asks = [OrderBookLevel(Decimal("50000.00"), Decimal("0.5"))]  # Lower than bid
        
        with pytest.raises(ValueError, match="Best bid must be less than best ask"):
            OrderBook(
                symbol="BTCUSDT",
                bids=bids,
                asks=asks,
                timestamp=timestamp
            )

    def test_order_book_immutability(self):
        """Test that OrderBook is immutable (frozen)."""
        timestamp = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        bids = [OrderBookLevel(Decimal("50000.00"), Decimal("1.0"))]
        asks = [OrderBookLevel(Decimal("50001.00"), Decimal("0.5"))]
        
        order_book = OrderBook(
            symbol="BTCUSDT",
            bids=bids,
            asks=asks,
            timestamp=timestamp
        )
        
        with pytest.raises(AttributeError):
            order_book.symbol = "ETHUSDT"


class TestTrade:
    """Test Trade value object."""

    def test_valid_trade(self):
        """Test creating valid trade."""
        timestamp = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        trade = Trade(
            symbol="BTCUSDT",
            trade_id="12345",
            price=Decimal("50000.00"),
            quantity=Decimal("1.5"),
            quote_quantity=Decimal("75000.00"),
            timestamp=timestamp,
            is_buyer_maker=True,
            trade_type=TradeType.BUY
        )
        
        assert trade.symbol == "BTCUSDT"
        assert trade.trade_id == "12345"
        assert trade.price == Decimal("50000.00")
        assert trade.quantity == Decimal("1.5")
        assert trade.quote_quantity == Decimal("75000.00")
        assert trade.timestamp == timestamp
        assert trade.is_buyer_maker is True
        assert trade.trade_type == TradeType.BUY

    def test_invalid_trade_price(self):
        """Test that invalid price raises ValueError."""
        timestamp = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        with pytest.raises(ValueError, match="Price must be positive"):
            Trade(
                symbol="BTCUSDT",
                trade_id="12345",
                price=Decimal("0"),
                quantity=Decimal("1.5"),
                quote_quantity=Decimal("75000.00"),
                timestamp=timestamp,
                is_buyer_maker=True,
                trade_type=TradeType.BUY
            )

    def test_invalid_trade_quantities(self):
        """Test that invalid quantities raise ValueError."""
        timestamp = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        with pytest.raises(ValueError, match="Quantity must be positive"):
            Trade(
                symbol="BTCUSDT",
                trade_id="12345",
                price=Decimal("50000.00"),
                quantity=Decimal("0"),
                quote_quantity=Decimal("75000.00"),
                timestamp=timestamp,
                is_buyer_maker=True,
                trade_type=TradeType.BUY
            )
        
        with pytest.raises(ValueError, match="Quote quantity must be positive"):
            Trade(
                symbol="BTCUSDT",
                trade_id="12345",
                price=Decimal("50000.00"),
                quantity=Decimal("1.5"),
                quote_quantity=Decimal("0"),
                timestamp=timestamp,
                is_buyer_maker=True,
                trade_type=TradeType.BUY
            )

    def test_trade_immutability(self):
        """Test that Trade is immutable (frozen)."""
        timestamp = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        trade = Trade(
            symbol="BTCUSDT",
            trade_id="12345",
            price=Decimal("50000.00"),
            quantity=Decimal("1.5"),
            quote_quantity=Decimal("75000.00"),
            timestamp=timestamp,
            is_buyer_maker=True,
            trade_type=TradeType.BUY
        )
        
        with pytest.raises(AttributeError):
            trade.price = Decimal("60000.00")


class TestFundingRate:
    """Test FundingRate value object."""

    def test_valid_funding_rate(self):
        """Test creating valid funding rate."""
        funding_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        next_funding_time = datetime(2024, 1, 1, 20, 0, 0, tzinfo=timezone.utc)
        
        funding_rate = FundingRate(
            symbol="BTCUSDT",
            funding_rate=Decimal("0.0001"),
            funding_time=funding_time,
            mark_price=Decimal("50000.00"),
            index_price=Decimal("49999.50"),
            next_funding_time=next_funding_time
        )
        
        assert funding_rate.symbol == "BTCUSDT"
        assert funding_rate.funding_rate == Decimal("0.0001")
        assert funding_rate.funding_time == funding_time
        assert funding_rate.mark_price == Decimal("50000.00")
        assert funding_rate.index_price == Decimal("49999.50")
        assert funding_rate.next_funding_time == next_funding_time

    def test_minimal_funding_rate(self):
        """Test creating funding rate with minimal data."""
        funding_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        funding_rate = FundingRate(
            symbol="ETHUSDT",
            funding_rate=Decimal("-0.0002"),
            funding_time=funding_time
        )
        
        assert funding_rate.mark_price is None
        assert funding_rate.index_price is None
        assert funding_rate.next_funding_time is None

    def test_funding_rate_immutability(self):
        """Test that FundingRate is immutable (frozen)."""
        funding_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        funding_rate = FundingRate(
            symbol="BTCUSDT",
            funding_rate=Decimal("0.0001"),
            funding_time=funding_time
        )
        
        with pytest.raises(AttributeError):
            funding_rate.funding_rate = Decimal("0.0002")


class TestMarketStats:
    """Test MarketStats value object."""

    def test_valid_market_stats(self):
        """Test creating valid market stats."""
        open_time = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        close_time = datetime(2024, 1, 1, 23, 59, 59, tzinfo=timezone.utc)
        
        stats = MarketStats(
            symbol="BTCUSDT",
            price_change=Decimal("1000.00"),
            price_change_percent=Decimal("2.0"),
            weighted_avg_price=Decimal("50500.00"),
            prev_close_price=Decimal("50000.00"),
            last_price=Decimal("51000.00"),
            last_qty=Decimal("0.5"),
            bid_price=Decimal("50999.00"),
            ask_price=Decimal("51001.00"),
            open_price=Decimal("50000.00"),
            high_price=Decimal("52000.00"),
            low_price=Decimal("49500.00"),
            volume=Decimal("10000.0"),
            quote_volume=Decimal("505000000.0"),
            open_time=open_time,
            close_time=close_time,
            first_id=1,
            last_id=50000,
            trade_count=50000
        )
        
        assert stats.symbol == "BTCUSDT"
        assert stats.price_change == Decimal("1000.00")
        assert stats.price_change_percent == Decimal("2.0")
        assert stats.last_price == Decimal("51000.00")
        assert stats.volume == Decimal("10000.0")
        assert stats.trade_count == 50000

    def test_market_stats_immutability(self):
        """Test that MarketStats is immutable (frozen)."""
        open_time = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        close_time = datetime(2024, 1, 1, 23, 59, 59, tzinfo=timezone.utc)
        
        stats = MarketStats(
            symbol="BTCUSDT",
            price_change=Decimal("1000.00"),
            price_change_percent=Decimal("2.0"),
            weighted_avg_price=Decimal("50500.00"),
            prev_close_price=Decimal("50000.00"),
            last_price=Decimal("51000.00"),
            last_qty=Decimal("0.5"),
            bid_price=Decimal("50999.00"),
            ask_price=Decimal("51001.00"),
            open_price=Decimal("50000.00"),
            high_price=Decimal("52000.00"),
            low_price=Decimal("49500.00"),
            volume=Decimal("10000.0"),
            quote_volume=Decimal("505000000.0"),
            open_time=open_time,
            close_time=close_time,
            first_id=1,
            last_id=50000,
            trade_count=50000
        )
        
        with pytest.raises(AttributeError):
            stats.last_price = Decimal("52000.00")


class TestMarketDataSubscription:
    """Test MarketDataSubscription entity."""

    def test_create_subscription(self):
        """Test creating a new market data subscription."""
        user_id = uuid.uuid4()
        data_types = [DataType.CANDLE, DataType.TRADE]
        intervals = [CandleInterval.ONE_MINUTE, CandleInterval.FIVE_MINUTE]
        
        with patch('src.trading.domain.market_data.dt') as mock_dt:
            mock_now = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
            mock_dt.now.return_value = mock_now
            mock_dt.timezone.utc = timezone.utc
            
            subscription = MarketDataSubscription.create(
                user_id=user_id,
                symbol="btcusdt",
                data_types=data_types,
                intervals=intervals,
                exchange="binance"
            )
        
        assert isinstance(subscription.id, uuid.UUID)
        assert subscription.user_id == user_id
        assert subscription.symbol == "BTCUSDT"  # Should be uppercase
        assert subscription.data_types == data_types
        assert subscription.intervals == intervals
        assert subscription.status == StreamStatus.CONNECTING
        assert subscription.created_at == mock_now
        assert subscription.updated_at == mock_now
        assert subscription.exchange == "BINANCE"  # Should be uppercase
        assert subscription.stream_url is None
        assert subscription.last_message_at is None
        assert subscription.error_message is None
        assert subscription.reconnect_count == 0
        assert subscription.metadata == {}

    def test_mark_connected(self):
        """Test marking subscription as connected."""
        subscription = MarketDataSubscription.create(
            user_id=uuid.uuid4(),
            symbol="BTCUSDT",
            data_types=[DataType.CANDLE],
            intervals=[CandleInterval.ONE_MINUTE],
            exchange="BINANCE"
        )
        
        stream_url = "wss://stream.binance.com/ws/btcusdt@kline_1m"
        
        with patch('src.trading.domain.market_data.dt') as mock_dt:
            mock_now = datetime(2024, 1, 1, 12, 30, 0, tzinfo=timezone.utc)
            mock_dt.now.return_value = mock_now
            mock_dt.timezone.utc = timezone.utc
            
            subscription.mark_connected(stream_url)
        
        assert subscription.status == StreamStatus.CONNECTED
        assert subscription.stream_url == stream_url
        assert subscription.last_message_at == mock_now
        assert subscription.updated_at == mock_now
        assert subscription.error_message is None

    def test_mark_disconnected(self):
        """Test marking subscription as disconnected."""
        subscription = MarketDataSubscription.create(
            user_id=uuid.uuid4(),
            symbol="BTCUSDT",
            data_types=[DataType.CANDLE],
            intervals=[CandleInterval.ONE_MINUTE],
            exchange="BINANCE"
        )
        
        subscription.mark_connected("wss://test.url")
        
        with patch('src.trading.domain.market_data.dt') as mock_dt:
            mock_now = datetime(2024, 1, 1, 13, 0, 0, tzinfo=timezone.utc)
            mock_dt.now.return_value = mock_now
            mock_dt.timezone.utc = timezone.utc
            
            subscription.mark_disconnected("Connection lost")
        
        assert subscription.status == StreamStatus.DISCONNECTED
        assert subscription.error_message == "Connection lost"
        assert subscription.updated_at == mock_now

    def test_mark_disconnected_no_reason(self):
        """Test marking subscription as disconnected without reason."""
        subscription = MarketDataSubscription.create(
            user_id=uuid.uuid4(),
            symbol="BTCUSDT",
            data_types=[DataType.CANDLE],
            intervals=[CandleInterval.ONE_MINUTE],
            exchange="BINANCE"
        )
        
        subscription.mark_connected("wss://test.url")
        subscription.mark_disconnected()
        
        assert subscription.status == StreamStatus.DISCONNECTED
        assert subscription.error_message is None

    def test_mark_error(self):
        """Test marking subscription as error."""
        subscription = MarketDataSubscription.create(
            user_id=uuid.uuid4(),
            symbol="BTCUSDT",
            data_types=[DataType.CANDLE],
            intervals=[CandleInterval.ONE_MINUTE],
            exchange="BINANCE"
        )
        
        subscription.mark_connected("wss://test.url")
        
        with patch('src.trading.domain.market_data.dt') as mock_dt:
            mock_now = datetime(2024, 1, 1, 14, 0, 0, tzinfo=timezone.utc)
            mock_dt.now.return_value = mock_now
            mock_dt.timezone.utc = timezone.utc
            
            subscription.mark_error("WebSocket error")
        
        assert subscription.status == StreamStatus.ERROR
        assert subscription.error_message == "WebSocket error"
        assert subscription.updated_at == mock_now

    def test_mark_reconnecting(self):
        """Test marking subscription as reconnecting."""
        subscription = MarketDataSubscription.create(
            user_id=uuid.uuid4(),
            symbol="BTCUSDT",
            data_types=[DataType.CANDLE],
            intervals=[CandleInterval.ONE_MINUTE],
            exchange="BINANCE"
        )
        
        subscription.mark_connected("wss://test.url")
        subscription.mark_disconnected("Connection lost")
        
        with patch('src.trading.domain.market_data.dt') as mock_dt:
            mock_now = datetime(2024, 1, 1, 15, 0, 0, tzinfo=timezone.utc)
            mock_dt.now.return_value = mock_now
            mock_dt.timezone.utc = timezone.utc
            
            subscription.mark_reconnecting()
        
        assert subscription.status == StreamStatus.RECONNECTING
        assert subscription.reconnect_count == 1
        assert subscription.updated_at == mock_now
        
        # Test multiple reconnections
        subscription.mark_reconnecting()
        assert subscription.reconnect_count == 2

    def test_update_last_message(self):
        """Test updating last message timestamp."""
        subscription = MarketDataSubscription.create(
            user_id=uuid.uuid4(),
            symbol="BTCUSDT",
            data_types=[DataType.CANDLE],
            intervals=[CandleInterval.ONE_MINUTE],
            exchange="BINANCE"
        )
        
        subscription.mark_connected("wss://test.url")
        
        with patch('src.trading.domain.market_data.dt') as mock_dt:
            mock_now = datetime(2024, 1, 1, 16, 0, 0, tzinfo=timezone.utc)
            mock_dt.now.return_value = mock_now
            mock_dt.timezone.utc = timezone.utc
            
            subscription.update_last_message()
        
        assert subscription.last_message_at == mock_now
        assert subscription.updated_at == mock_now

    def test_is_active(self):
        """Test checking if subscription is active."""
        subscription = MarketDataSubscription.create(
            user_id=uuid.uuid4(),
            symbol="BTCUSDT",
            data_types=[DataType.CANDLE],
            intervals=[CandleInterval.ONE_MINUTE],
            exchange="BINANCE"
        )
        
        # Initially connecting - not active
        assert subscription.is_active() is False
        
        # Connected - active
        subscription.mark_connected("wss://test.url")
        assert subscription.is_active() is True
        
        # Reconnecting - still active
        subscription.mark_reconnecting()
        assert subscription.is_active() is True
        
        # Disconnected - not active
        subscription.mark_disconnected()
        assert subscription.is_active() is False
        
        # Error - not active
        subscription.mark_error("Error")
        assert subscription.is_active() is False