"""SQLAlchemy models for trading tables: Orders, Positions, Trades."""
from sqlalchemy import Column, String, Integer, ForeignKey, Index, CheckConstraint, Numeric, DECIMAL, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from decimal import Decimal

from .base import TimestampMixin, SoftDeleteMixin, UUIDPrimaryKeyMixin
from ..database import Base

# Cross-database JSON type (JSONB for PostgreSQL, JSON for SQLite)
JSONType = JSON().with_variant(JSONB(), "postgresql")


class OrderModel(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """Order model with partitioning support."""
    
    __tablename__ = "orders"
    __table_args__ = (
        Index('idx_orders_user_symbol_exchange', 'user_id', 'symbol', 'exchange_id', 'created_at'),
        Index('idx_orders_status_created', 'status', 'created_at'),
        Index('idx_orders_exchange_order_id', 'exchange_order_id', unique=True),
        Index('idx_orders_position_id', 'position_id'),
        Index('idx_orders_bot_id', 'bot_id'),
        Index('idx_orders_deleted_at', 'deleted_at'),
        CheckConstraint("side IN ('LONG', 'SHORT')", name='ck_orders_side'),
        CheckConstraint("order_type IN ('MARKET', 'LIMIT', 'STOP_MARKET', 'STOP_LIMIT', 'TRAILING_STOP')", name='ck_orders_type'),
        CheckConstraint("status IN ('PENDING', 'PARTIALLY_FILLED', 'FILLED', 'CANCELLED', 'REJECTED', 'EXPIRED')", name='ck_orders_status'),
        CheckConstraint("time_in_force IN ('GTC', 'IOC', 'FOK', 'GTX')", name='ck_orders_tif'),
        CheckConstraint("margin_mode IN ('ISOLATED', 'CROSS')", name='ck_orders_margin_mode'),
        CheckConstraint("position_mode IN ('ONE_WAY', 'HEDGE')", name='ck_orders_position_mode'),
        CheckConstraint('leverage >= 1 AND leverage <= 125', name='ck_orders_leverage'),
        {'comment': 'Trading orders (partitioned by created_at monthly)'}
    )
    
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    position_id = Column(UUID(as_uuid=True), ForeignKey('positions.id', ondelete='SET NULL'), nullable=True, comment="Associated position ID")
    bot_id = Column(UUID(as_uuid=True), ForeignKey('bots.id', ondelete='SET NULL'), nullable=True, comment="Bot that created this order")
    exchange_id = Column(Integer, ForeignKey('exchanges.id', ondelete='RESTRICT'), nullable=False)
    symbol = Column(String(20), nullable=False, comment="Trading symbol (BTCUSDT)")
    
    # Order details
    side = Column(String(10), nullable=False, comment="LONG or SHORT")
    order_type = Column(String(20), nullable=False, comment="Order type")
    quantity = Column(DECIMAL(20, 8), nullable=False, comment="Order quantity")
    price = Column(DECIMAL(20, 8), nullable=True, comment="Limit price (NULL for MARKET)")
    stop_price = Column(DECIMAL(20, 8), nullable=True, comment="Stop trigger price")
    callback_rate = Column(DECIMAL(5, 2), nullable=True, comment="Trailing stop callback rate (%)")
    
    # Futures-specific
    leverage = Column(Integer, nullable=False, default=1, comment="Leverage (1-125)")
    margin_mode = Column(String(10), nullable=False, default="ISOLATED", comment="ISOLATED or CROSS")
    position_mode = Column(String(10), nullable=False, default="ONE_WAY", comment="ONE_WAY or HEDGE")
    time_in_force = Column(String(10), nullable=False, default="GTC", comment="Time in force")
    
    # Risk management
    stop_loss = Column(DECIMAL(20, 8), nullable=True, comment="Stop loss price")
    take_profit = Column(DECIMAL(20, 8), nullable=True, comment="Take profit price")
    
    # Status tracking
    status = Column(String(20), nullable=False, default="PENDING", comment="Order status")
    exchange_order_id = Column(String(100), nullable=True, unique=True, comment="Exchange order ID")
    filled_quantity = Column(DECIMAL(20, 8), nullable=False, default=Decimal("0"), comment="Filled quantity")
    filled_avg_price = Column(DECIMAL(20, 8), nullable=True, comment="Average fill price")
    
    # Metadata
    meta_data = Column(JSONType, nullable=True, default={}, comment="Additional order metadata")
    filled_at = Column(TimestampMixin.created_at.type, nullable=True, comment="Order filled timestamp")
    cancelled_at = Column(TimestampMixin.created_at.type, nullable=True, comment="Order cancelled timestamp")
    
    # Relationships
    user = relationship("UserModel", back_populates="orders")
    exchange = relationship("ExchangeModel", back_populates="orders")
    position = relationship("PositionModel", back_populates="orders", foreign_keys=[position_id])
    bot = relationship("BotModel", back_populates="orders")
    symbol_ref = relationship("SymbolModel", foreign_keys=[symbol, exchange_id], 
                              primaryjoin="and_(OrderModel.symbol==SymbolModel.symbol, OrderModel.exchange_id==SymbolModel.exchange_id)",
                              viewonly=True)
    trades = relationship("TradeModel", back_populates="order")


class PositionModel(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """Position model with partitioning support."""
    
    __tablename__ = "positions"
    __table_args__ = (
        Index('idx_positions_user_symbol_status', 'user_id', 'symbol', 'exchange_id', 'status'),
        Index('idx_positions_bot_opened', 'bot_id', 'opened_at'),
        Index('idx_positions_deleted_at', 'deleted_at'),
        CheckConstraint("side IN ('LONG', 'SHORT')", name='ck_positions_side'),
        CheckConstraint("status IN ('OPEN', 'CLOSED', 'LIQUIDATED')", name='ck_positions_status'),
        CheckConstraint("margin_mode IN ('ISOLATED', 'CROSS')", name='ck_positions_margin_mode'),
        CheckConstraint('leverage >= 1 AND leverage <= 125', name='ck_positions_leverage'),
        {'comment': 'Trading positions (partitioned by opened_at quarterly)'}
    )
    
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    bot_id = Column(UUID(as_uuid=True), ForeignKey('bots.id', ondelete='SET NULL'), nullable=True, comment="Bot managing this position")
    exchange_id = Column(Integer, ForeignKey('exchanges.id', ondelete='RESTRICT'), nullable=False)
    symbol = Column(String(20), nullable=False, comment="Trading symbol")
    
    # Position details
    side = Column(String(10), nullable=False, comment="LONG or SHORT")
    entry_price = Column(DECIMAL(20, 8), nullable=False, comment="Average entry price")
    mark_price = Column(DECIMAL(20, 8), nullable=True, comment="Current mark price")
    liquidation_price = Column(DECIMAL(20, 8), nullable=True, comment="Liquidation price")
    quantity = Column(DECIMAL(20, 8), nullable=False, comment="Position size")
    
    # P&L tracking
    pnl = Column(DECIMAL(20, 8), nullable=False, default=Decimal("0"), comment="Total P&L")
    pnl_percent = Column(DECIMAL(10, 4), nullable=False, default=Decimal("0"), comment="P&L percentage")
    unrealized_pnl = Column(DECIMAL(20, 8), nullable=False, default=Decimal("0"), comment="Unrealized P&L")
    realized_pnl = Column(DECIMAL(20, 8), nullable=False, default=Decimal("0"), comment="Realized P&L")
    
    # Risk management
    stop_loss = Column(DECIMAL(20, 8), nullable=True, comment="Stop loss price")
    take_profit = Column(DECIMAL(20, 8), nullable=True, comment="Take profit price")
    
    # Futures-specific
    leverage = Column(Integer, nullable=False, default=1, comment="Position leverage")
    margin_mode = Column(String(10), nullable=False, default="ISOLATED", comment="Margin mode")
    margin_used = Column(DECIMAL(20, 8), nullable=False, default=Decimal("0"), comment="Margin required")
    
    # Status
    status = Column(String(20), nullable=False, default="OPEN", comment="Position status")
    opened_at = Column(TimestampMixin.created_at.type, nullable=False, comment="Position opened timestamp")
    closed_at = Column(TimestampMixin.created_at.type, nullable=True, comment="Position closed timestamp")
    
    # Relationships
    user = relationship("UserModel", back_populates="positions")
    exchange = relationship("ExchangeModel", back_populates="positions")
    bot = relationship("BotModel", back_populates="positions")
    symbol_ref = relationship("SymbolModel", foreign_keys=[symbol, exchange_id],
                              primaryjoin="and_(PositionModel.symbol==SymbolModel.symbol, PositionModel.exchange_id==SymbolModel.exchange_id)",
                              viewonly=True)
    orders = relationship("OrderModel", back_populates="position", foreign_keys="OrderModel.position_id")
    trades = relationship("TradeModel", back_populates="position")


class TradeModel(Base, UUIDPrimaryKeyMixin):
    """Trade execution record (immutable, no soft delete)."""
    
    __tablename__ = "trades"
    __table_args__ = (
        Index('idx_trades_position_executed', 'position_id', 'executed_at'),
        Index('idx_trades_order_id', 'order_id'),
        Index('idx_trades_exchange_trade_id', 'exchange_trade_id', unique=True),
        CheckConstraint("side IN ('BUY', 'SELL')", name='ck_trades_side'),
        CheckConstraint("status IN ('SUCCESS', 'FAILED')", name='ck_trades_status'),
        {'comment': 'Trade executions (immutable, partitioned by executed_at monthly)'}
    )
    
    position_id = Column(UUID(as_uuid=True), ForeignKey('positions.id', ondelete='RESTRICT'), nullable=False)
    order_id = Column(UUID(as_uuid=True), ForeignKey('orders.id', ondelete='RESTRICT'), nullable=False)
    exchange_id = Column(Integer, ForeignKey('exchanges.id', ondelete='RESTRICT'), nullable=False)
    symbol = Column(String(20), nullable=False, comment="Trading symbol")
    
    # Trade details
    side = Column(String(10), nullable=False, comment="BUY or SELL")
    price = Column(DECIMAL(20, 8), nullable=False, comment="Execution price")
    quantity = Column(DECIMAL(20, 8), nullable=False, comment="Executed quantity")
    
    # Fees
    fee = Column(DECIMAL(20, 8), nullable=False, default=Decimal("0"), comment="Trading fee")
    fee_currency = Column(String(10), nullable=True, comment="Fee currency")
    
    # P&L
    pnl = Column(DECIMAL(20, 8), nullable=True, comment="P&L for this trade")
    
    # Status
    status = Column(String(20), nullable=False, default="SUCCESS", comment="Trade status")
    exchange_trade_id = Column(String(100), nullable=True, unique=True, comment="Exchange trade ID")
    
    # Metadata
    meta_data = Column(JSONType, nullable=True, default={}, comment="Additional trade metadata")
    executed_at = Column(TimestampMixin.created_at.type, nullable=False, comment="Trade execution timestamp")
    
    # Relationships
    position = relationship("PositionModel", back_populates="trades")
    order = relationship("OrderModel", back_populates="trades")
