"""Market data domain models for real-time market information."""
from dataclasses import dataclass, field
from datetime import datetime as dt, timezone as dt_timezone
from enum import Enum
from typing import Optional, List, Dict, Any
from decimal import Decimal
import uuid


class DataType(str, Enum):
    """Market data type enumeration."""
    TICK = "TICK"                    # Individual trade data
    CANDLE = "CANDLE"                # OHLCV candle data
    ORDER_BOOK = "ORDER_BOOK"        # Order book depth
    TRADE = "TRADE"                  # Trade execution data
    FUNDING_RATE = "FUNDING_RATE"    # Futures funding rate
    MARK_PRICE = "MARK_PRICE"        # Mark price for futures


class CandleInterval(str, Enum):
    """Candle time interval enumeration."""
    ONE_MINUTE = "1m"
    THREE_MINUTE = "3m"
    FIVE_MINUTE = "5m"
    FIFTEEN_MINUTE = "15m"
    THIRTY_MINUTE = "30m"
    ONE_HOUR = "1h"
    TWO_HOUR = "2h"
    FOUR_HOUR = "4h"
    SIX_HOUR = "6h"
    EIGHT_HOUR = "8h"
    TWELVE_HOUR = "12h"
    ONE_DAY = "1d"
    THREE_DAY = "3d"
    ONE_WEEK = "1w"
    ONE_MONTH = "1M"


class TradeType(str, Enum):
    """Trade type enumeration."""
    BUY = "BUY"
    SELL = "SELL"


class StreamStatus(str, Enum):
    """Stream status enumeration."""
    CONNECTING = "CONNECTING"
    CONNECTED = "CONNECTED"
    DISCONNECTED = "DISCONNECTED"
    ERROR = "ERROR"
    RECONNECTING = "RECONNECTING"


@dataclass(frozen=True)
class Tick:
    """Individual price tick data."""
    symbol: str
    price: Decimal
    size: Decimal
    timestamp: dt
    trade_id: Optional[str] = None
    is_buyer_maker: Optional[bool] = None
    
    def __post_init__(self):
        if self.price <= 0:
            raise ValueError("Price must be positive")
        if self.size <= 0:
            raise ValueError("Size must be positive")


@dataclass(frozen=True)
class Candle:
    """OHLCV candle data."""
    symbol: str
    interval: CandleInterval
    open_price: Decimal
    high_price: Decimal
    low_price: Decimal
    close_price: Decimal
    volume: Decimal
    quote_volume: Decimal
    open_time: dt
    close_time: dt
    trade_count: int = 0
    taker_buy_volume: Optional[Decimal] = None
    taker_buy_quote_volume: Optional[Decimal] = None
    
    def __post_init__(self):
        if self.open_price <= 0:
            raise ValueError("Open price must be positive")
        if self.high_price <= 0:
            raise ValueError("High price must be positive")
        if self.low_price <= 0:
            raise ValueError("Low price must be positive")
        if self.close_price <= 0:
            raise ValueError("Close price must be positive")
        if self.volume < 0:
            raise ValueError("Volume cannot be negative")
        if self.quote_volume < 0:
            raise ValueError("Quote volume cannot be negative")
        if self.open_time >= self.close_time:
            raise ValueError("Open time must be before close time")
        
        # Price validation
        if not (self.low_price <= self.open_price <= self.high_price):
            raise ValueError("Open price must be between low and high")
        if not (self.low_price <= self.close_price <= self.high_price):
            raise ValueError("Close price must be between low and high")
    
    @property
    def price_change(self) -> Decimal:
        """Calculate price change from open to close."""
        return self.close_price - self.open_price
    
    @property
    def price_change_percent(self) -> Decimal:
        """Calculate percentage price change."""
        if self.open_price == 0:
            return Decimal("0")
        return (self.price_change / self.open_price) * 100
    
    @property
    def typical_price(self) -> Decimal:
        """Calculate typical price (HLC/3)."""
        return (self.high_price + self.low_price + self.close_price) / 3
    
    @property
    def weighted_price(self) -> Decimal:
        """Calculate volume weighted average price."""
        if self.volume == 0:
            return self.typical_price
        return self.quote_volume / self.volume


@dataclass(frozen=True)
class OrderBookLevel:
    """Single order book level (price and quantity)."""
    price: Decimal
    quantity: Decimal
    
    def __post_init__(self):
        if self.price <= 0:
            raise ValueError("Price must be positive")
        if self.quantity < 0:
            raise ValueError("Quantity cannot be negative")


@dataclass(frozen=True)
class OrderBook:
    """Order book depth data."""
    symbol: str
    bids: List[OrderBookLevel]  # Sorted by price descending
    asks: List[OrderBookLevel]  # Sorted by price ascending
    timestamp: dt
    last_update_id: Optional[int] = None
    
    def __post_init__(self):
        # Validate bid ordering (highest price first)
        for i in range(1, len(self.bids)):
            if self.bids[i].price >= self.bids[i-1].price:
                raise ValueError("Bids must be sorted by price descending")
        
        # Validate ask ordering (lowest price first)
        for i in range(1, len(self.asks)):
            if self.asks[i].price <= self.asks[i-1].price:
                raise ValueError("Asks must be sorted by price ascending")
        
        # Validate spread (best bid < best ask)
        if self.bids and self.asks:
            if self.best_bid_price >= self.best_ask_price:
                raise ValueError("Best bid must be less than best ask")
    
    @property
    def best_bid(self) -> Optional[OrderBookLevel]:
        """Get best bid (highest price)."""
        return self.bids[0] if self.bids else None
    
    @property
    def best_ask(self) -> Optional[OrderBookLevel]:
        """Get best ask (lowest price)."""
        return self.asks[0] if self.asks else None
    
    @property
    def best_bid_price(self) -> Optional[Decimal]:
        """Get best bid price."""
        return self.best_bid.price if self.best_bid else None
    
    @property
    def best_ask_price(self) -> Optional[Decimal]:
        """Get best ask price."""
        return self.best_ask.price if self.best_ask else None
    
    @property
    def spread(self) -> Optional[Decimal]:
        """Calculate bid-ask spread."""
        if self.best_bid_price and self.best_ask_price:
            return self.best_ask_price - self.best_bid_price
        return None
    
    @property
    def spread_percent(self) -> Optional[Decimal]:
        """Calculate bid-ask spread as percentage of mid price."""
        if self.spread and self.mid_price:
            return (self.spread / self.mid_price) * 100
        return None
    
    @property
    def mid_price(self) -> Optional[Decimal]:
        """Calculate mid price between best bid and ask."""
        if self.best_bid_price and self.best_ask_price:
            return (self.best_bid_price + self.best_ask_price) / 2
        return None
    
    def get_bid_depth(self, price: Decimal) -> Decimal:
        """Get total bid quantity at or above given price."""
        return sum(level.quantity for level in self.bids if level.price >= price)
    
    def get_ask_depth(self, price: Decimal) -> Decimal:
        """Get total ask quantity at or below given price."""
        return sum(level.quantity for level in self.asks if level.price <= price)


@dataclass(frozen=True)
class Trade:
    """Individual trade execution data."""
    symbol: str
    trade_id: str
    price: Decimal
    quantity: Decimal
    quote_quantity: Decimal
    timestamp: dt
    is_buyer_maker: bool
    trade_type: TradeType
    
    def __post_init__(self):
        if self.price <= 0:
            raise ValueError("Price must be positive")
        if self.quantity <= 0:
            raise ValueError("Quantity must be positive")
        if self.quote_quantity <= 0:
            raise ValueError("Quote quantity must be positive")


@dataclass(frozen=True)
class FundingRate:
    """Futures funding rate data."""
    symbol: str
    funding_rate: Decimal
    funding_time: dt
    mark_price: Optional[Decimal] = None
    index_price: Optional[Decimal] = None
    next_funding_time: Optional[dt] = None


@dataclass(frozen=True)
class MarketStats:
    """24h market statistics."""
    symbol: str
    price_change: Decimal
    price_change_percent: Decimal
    weighted_avg_price: Decimal
    prev_close_price: Decimal
    last_price: Decimal
    last_qty: Decimal
    bid_price: Decimal
    ask_price: Decimal
    open_price: Decimal
    high_price: Decimal
    low_price: Decimal
    volume: Decimal
    quote_volume: Decimal
    open_time: dt
    close_time: dt
    first_id: int
    last_id: int
    trade_count: int


@dataclass
class MarketDataSubscription:
    """Market data subscription entity."""
    id: uuid.UUID
    user_id: uuid.UUID
    symbol: str
    data_types: List[DataType]
    intervals: List[CandleInterval]  # For candle data
    status: StreamStatus
    created_at: dt
    updated_at: dt
    
    # Connection info
    exchange: str
    stream_url: Optional[str] = None
    last_message_at: Optional[dt] = None
    error_message: Optional[str] = None
    reconnect_count: int = 0
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def create(
        cls,
        user_id: uuid.UUID,
        symbol: str,
        data_types: List[DataType],
        intervals: List[CandleInterval],
        exchange: str,
    ) -> "MarketDataSubscription":
        """Create a new market data subscription."""
        now = dt.now(dt_timezone.utc)
        
        return cls(
            id=uuid.uuid4(),
            user_id=user_id,
            symbol=symbol.upper(),
            data_types=data_types,
            intervals=intervals,
            status=StreamStatus.CONNECTING,
            created_at=now,
            updated_at=now,
            exchange=exchange.upper(),
        )
    
    def mark_connected(self, stream_url: str) -> None:
        """Mark subscription as connected."""
        self.status = StreamStatus.CONNECTED
        self.stream_url = stream_url
        self.last_message_at = dt.now(dt_timezone.utc)
        self.updated_at = dt.now(dt_timezone.utc)
        self.error_message = None
    
    def mark_disconnected(self, error_message: Optional[str] = None) -> None:
        """Mark subscription as disconnected."""
        self.status = StreamStatus.DISCONNECTED
        self.error_message = error_message
        self.updated_at = dt.now(dt_timezone.utc)
    
    def mark_error(self, error_message: str) -> None:
        """Mark subscription as having an error."""
        self.status = StreamStatus.ERROR
        self.error_message = error_message
        self.updated_at = dt.now(dt_timezone.utc)
    
    def mark_reconnecting(self) -> None:
        """Mark subscription as reconnecting."""
        self.status = StreamStatus.RECONNECTING
        self.reconnect_count += 1
        self.updated_at = dt.now(dt_timezone.utc)
    
    def update_last_message(self) -> None:
        """Update last message timestamp."""
        self.last_message_at = dt.now(dt_timezone.utc)
        self.updated_at = dt.now(dt_timezone.utc)
    
    def is_active(self) -> bool:
        """Check if subscription is active."""
        return self.status in [StreamStatus.CONNECTED, StreamStatus.RECONNECTING]


__all__ = [
    "DataType",
    "CandleInterval",
    "TradeType",
    "StreamStatus",
    "Tick",
    "Candle",
    "OrderBookLevel",
    "OrderBook",
    "Trade",
    "FundingRate",
    "MarketStats",
    "MarketDataSubscription",
]