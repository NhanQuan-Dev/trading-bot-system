"""SQLAlchemy models for market data tables."""
from sqlalchemy import Column, String, Integer, ForeignKey, Index, CheckConstraint, DECIMAL, BigInteger, Boolean, DateTime, JSON
from sqlalchemy.dialects.postgresql import JSONB, ARRAY, UUID
from sqlalchemy.orm import relationship
from decimal import Decimal

from .base import TimestampMixin, UUIDPrimaryKeyMixin
from ..database import Base

# Cross-database JSON type (JSONB for PostgreSQL, JSON for SQLite)
JSONType = JSON().with_variant(JSONB(), "postgresql")


class MarketDataSubscriptionModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Market data subscription model."""
    
    __tablename__ = "market_data_subscriptions"
    __table_args__ = (
        Index('idx_subscriptions_user_symbol', 'user_id', 'symbol'),
        Index('idx_subscriptions_status', 'status'),
        Index('idx_subscriptions_exchange', 'exchange'),
        CheckConstraint("status IN ('CONNECTING', 'CONNECTED', 'DISCONNECTED', 'ERROR', 'RECONNECTING')", name='ck_subscription_status'),
        {'comment': 'Market data subscriptions for real-time streaming'}
    )
    
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    symbol = Column(String(20), nullable=False, comment="Trading symbol")
    data_types = Column(ARRAY(String(20)), nullable=False, comment="Subscribed data types")
    intervals = Column(ARRAY(String(5)), nullable=False, default=[], comment="Candle intervals")
    status = Column(String(20), nullable=False, default="CONNECTING", comment="Subscription status")
    exchange = Column(String(20), nullable=False, default="BINANCE", comment="Exchange name")
    stream_url = Column(String(500), nullable=True, comment="WebSocket stream URL")
    last_message_at = Column(DateTime(timezone=True), nullable=True, comment="Last message received")
    error_message = Column(String(1000), nullable=True, comment="Error message if any")
    reconnect_count = Column(Integer, nullable=False, default=0, comment="Reconnection attempts")
    meta_data = Column(JSONType, nullable=False, default={}, comment="Additional metadata")
    
    # Relationships
    user = relationship("UserModel", back_populates="market_data_subscriptions")


class MarketPriceModel(Base):
    """Market price OHLCV data (time-series, no soft delete)."""
    
    __tablename__ = "market_prices"
    __table_args__ = (
        Index('idx_market_prices_symbol_interval_time', 'symbol', 'exchange_id', 'interval', 'timestamp', unique=True),
        CheckConstraint("interval IN ('1m', '5m', '15m', '1h', '4h', '1d', '1w')", name='ck_market_prices_interval'),
        {'comment': 'OHLCV market data (partitioned by timestamp)'}
    )
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="Auto-increment ID")
    symbol = Column(String(20), nullable=False, comment="Trading symbol")
    exchange_id = Column(Integer, ForeignKey('exchanges.id', ondelete='RESTRICT'), nullable=False)
    interval = Column(String(10), nullable=False, comment="Candle interval")
    timestamp = Column(TimestampMixin.created_at.type, nullable=False, comment="Candle open time (UTC)")
    
    # OHLCV data
    open = Column(DECIMAL(20, 8), nullable=False, comment="Open price")
    high = Column(DECIMAL(20, 8), nullable=False, comment="High price")
    low = Column(DECIMAL(20, 8), nullable=False, comment="Low price")
    close = Column(DECIMAL(20, 8), nullable=False, comment="Close price")
    volume = Column(DECIMAL(20, 8), nullable=False, comment="Volume in base asset")
    
    # Additional metrics
    quote_volume = Column(DECIMAL(20, 8), nullable=True, comment="Volume in quote asset")
    num_trades = Column(Integer, nullable=True, comment="Number of trades")
    taker_buy_base_volume = Column(DECIMAL(20, 8), nullable=True, comment="Taker buy volume (base)")
    taker_buy_quote_volume = Column(DECIMAL(20, 8), nullable=True, comment="Taker buy volume (quote)")
    
    # Relationships
    symbol_ref = relationship("SymbolModel", foreign_keys=[symbol, exchange_id],
                              primaryjoin="and_(MarketPriceModel.symbol==SymbolModel.symbol, MarketPriceModel.exchange_id==SymbolModel.exchange_id)",
                              viewonly=True)


class OrderBookSnapshotModel(Base):
    """Order book snapshot (time-series, no soft delete)."""
    
    __tablename__ = "orderbook_snapshots"
    __table_args__ = (
        Index('idx_orderbook_symbol_time', 'symbol', 'exchange_id', 'timestamp'),
        {'comment': 'Order book depth snapshots (partitioned by timestamp daily)'}
    )
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="Auto-increment ID")
    symbol = Column(String(20), nullable=False, comment="Trading symbol")
    exchange_id = Column(Integer, ForeignKey('exchanges.id', ondelete='RESTRICT'), nullable=False)
    timestamp = Column(TimestampMixin.created_at.type, nullable=False, comment="Snapshot timestamp (UTC)")
    
    # Order book data (JSON arrays)
    bids = Column(JSONType, nullable=False, default=[], comment="Bid orders [[price, quantity], ...]")
    asks = Column(JSONType, nullable=False, default=[], comment="Ask orders [[price, quantity], ...]")
    
    # Aggregated metrics
    total_bid_volume = Column(DECIMAL(20, 8), nullable=True, comment="Total bid volume")
    total_ask_volume = Column(DECIMAL(20, 8), nullable=True, comment="Total ask volume")
    spread = Column(DECIMAL(20, 8), nullable=True, comment="Best bid-ask spread")
    mid_price = Column(DECIMAL(20, 8), nullable=True, comment="Mid price")
    
    # Relationships
    symbol_ref = relationship("SymbolModel", foreign_keys=[symbol, exchange_id],
                              primaryjoin="and_(OrderBookSnapshotModel.symbol==SymbolModel.symbol, OrderBookSnapshotModel.exchange_id==SymbolModel.exchange_id)",
                              viewonly=True)
