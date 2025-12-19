"""SQLAlchemy models for core tables: Users, Exchanges, API Connections."""
from sqlalchemy import Column, String, Boolean, Integer, JSON, ForeignKey, UniqueConstraint, Index, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime

from .base import TimestampMixin, SoftDeleteMixin, UUIDPrimaryKeyMixin
from ..database import Base

# Cross-database JSON type (JSONB for PostgreSQL, JSON for SQLite)
JSONType = JSON().with_variant(JSONB(), "postgresql")


class UserModel(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """User account model."""
    
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint('email', name='uq_users_email'),
        Index('idx_users_email', 'email'),
        Index('idx_users_created_at', 'created_at'),
        Index('idx_users_deleted_at', 'deleted_at'),
        {'comment': 'User accounts with authentication'}
    )
    
    email = Column(String(255), nullable=False, unique=True, comment="User email (unique)")
    password_hash = Column(String(255), nullable=False, comment="Bcrypt password hash")
    full_name = Column(String(255), nullable=True, comment="User full name")
    timezone = Column(String(50), nullable=False, default="UTC", comment="User timezone")
    last_login = Column(TimestampMixin.created_at.type, nullable=True, comment="Last login timestamp")
    is_active = Column(Boolean, nullable=False, default=True, comment="Account active status")
    preferences = Column(JSONType, nullable=True, default={}, comment="User preferences (JSON)")
    
    # Relationships
    bots = relationship("BotModel", back_populates="user", cascade="all, delete-orphan")
    strategies = relationship("StrategyModel", back_populates="user", cascade="all, delete-orphan")
    orders = relationship("OrderModel", back_populates="user")
    positions = relationship("PositionModel", back_populates="user")
    api_connections = relationship("APIConnectionModel", back_populates="user", cascade="all, delete-orphan")
    database_configs = relationship("DatabaseConfigModel", back_populates="user", cascade="all, delete-orphan")
    alerts = relationship("AlertModel", back_populates="user", cascade="all, delete-orphan")
    risk_limits = relationship("RiskLimitModel", back_populates="user", cascade="all, delete-orphan")
    risk_alerts = relationship("RiskAlertModel", back_populates="user", cascade="all, delete-orphan")
    market_data_subscriptions = relationship("MarketDataSubscriptionModel", back_populates="user", cascade="all, delete-orphan")


class ExchangeModel(Base, TimestampMixin):
    """Exchange configuration model."""
    
    __tablename__ = "exchanges"
    __table_args__ = (
        UniqueConstraint('code', name='uq_exchanges_code'),
        Index('idx_exchanges_code', 'code'),
        {'comment': 'Supported exchange configurations'}
    )
    
    id = Column(Integer, primary_key=True, autoincrement=True, comment="Auto-increment ID")
    code = Column(String(50), nullable=False, unique=True, comment="Exchange code (BINANCE, BYBIT, OKX)")
    name = Column(String(100), nullable=False, comment="Exchange display name")
    api_base_url = Column(String(255), nullable=False, comment="Exchange API base URL")
    supported_features = Column(JSONType, nullable=True, default={}, comment="Supported features (futures, spot, margin)")
    is_active = Column(Boolean, nullable=False, default=True, comment="Exchange active status")
    rate_limits = Column(JSONType, nullable=True, default={}, comment="API rate limits configuration")
    
    # Relationships
    symbols = relationship("SymbolModel", back_populates="exchange")
    orders = relationship("OrderModel", back_populates="exchange")
    positions = relationship("PositionModel", back_populates="exchange")
    api_connections = relationship("APIConnectionModel", back_populates="exchange")


class APIConnectionModel(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """User API connection credentials (encrypted)."""
    
    __tablename__ = "api_connections"
    __table_args__ = (
        Index('idx_api_connections_user_exchange', 'user_id', 'exchange_id'),
        Index('idx_api_connections_deleted_at', 'deleted_at'),
        {'comment': 'User exchange API credentials (encrypted)'}
    )
    
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    exchange_id = Column(Integer, ForeignKey('exchanges.id', ondelete='RESTRICT'), nullable=False)
    name = Column(String(100), nullable=False, comment="Connection name (user-defined)")
    
    # Mainnet credentials
    api_key_encrypted = Column(Text, nullable=False, comment="Encrypted mainnet API key (Fernet)")
    secret_key_encrypted = Column(Text, nullable=False, comment="Encrypted mainnet secret key (Fernet)")
    passphrase_encrypted = Column(Text, nullable=True, comment="Encrypted passphrase (for some exchanges)")
    
    # Testnet credentials (optional)
    testnet_api_key_encrypted = Column(Text, nullable=True, comment="Encrypted testnet API key (Fernet)")
    testnet_secret_key_encrypted = Column(Text, nullable=True, comment="Encrypted testnet secret key (Fernet)")
    # Whether this connection should use testnet endpoints by default
    is_testnet = Column(Boolean, nullable=False, default=False, comment="Use testnet endpoints")
    
    is_active = Column(Boolean, nullable=False, default=True, comment="Connection active status")
    permissions = Column(JSONType, nullable=True, default={}, comment="API key permissions")
    last_used_at = Column(TimestampMixin.created_at.type, nullable=True, comment="Last time credentials were used")
    
    # Relationships
    user = relationship("UserModel", back_populates="api_connections")
    exchange = relationship("ExchangeModel", back_populates="api_connections")
    bots = relationship("BotModel", back_populates="exchange_connection")


class DatabaseConfigModel(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """User external database configuration (encrypted)."""
    
    __tablename__ = "database_configs"
    __table_args__ = (
        Index('idx_database_configs_user_id', 'user_id'),
        Index('idx_database_configs_deleted_at', 'deleted_at'),
        {'comment': 'User external database configurations (encrypted)'}
    )
    
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    name = Column(String(100), nullable=False, comment="Database connection name")
    db_type = Column(String(50), nullable=False, comment="Database type (postgresql, mysql, mongodb, etc.)")
    host = Column(String(255), nullable=False, comment="Database host")
    port = Column(Integer, nullable=False, comment="Database port")
    database_name = Column(String(100), nullable=False, comment="Database name")
    username = Column(String(100), nullable=False, comment="Database username")
    password_encrypted = Column(Text, nullable=False, comment="Encrypted password (Fernet)")
    is_active = Column(Boolean, nullable=False, default=True, comment="Configuration active status")
    connection_params = Column(JSONType, nullable=True, default={}, comment="Additional connection parameters")
    last_tested_at = Column(TimestampMixin.created_at.type, nullable=True, comment="Last connection test timestamp")
    
    # Relationships
    user = relationship("UserModel", back_populates="database_configs")


class SymbolModel(Base, TimestampMixin):
    """Trading symbol/pair model."""
    
    __tablename__ = "symbols"
    __table_args__ = (
        UniqueConstraint('symbol', 'exchange_id', name='uq_symbols_symbol_exchange'),
        Index('idx_symbols_exchange_status', 'exchange_id', 'status'),
        Index('idx_symbols_symbol', 'symbol'),
        {'comment': 'Trading symbols/pairs for each exchange'}
    )
    
    symbol = Column(String(20), primary_key=True, comment="Symbol code (BTCUSDT)")
    exchange_id = Column(Integer, ForeignKey('exchanges.id', ondelete='RESTRICT'), primary_key=True)
    base_asset = Column(String(20), nullable=False, comment="Base asset (BTC)")
    quote_asset = Column(String(20), nullable=False, comment="Quote asset (USDT)")
    status = Column(String(20), nullable=False, default="TRADING", comment="Symbol status (TRADING, HALT, DELISTED)")
    contract_type = Column(String(20), nullable=True, comment="Contract type (PERPETUAL, QUARTERLY, etc.)")
    price_precision = Column(Integer, nullable=False, default=8, comment="Price decimal precision")
    quantity_precision = Column(Integer, nullable=False, default=8, comment="Quantity decimal precision")
    min_order_qty = Column(String(50), nullable=True, comment="Minimum order quantity")
    max_order_qty = Column(String(50), nullable=True, comment="Maximum order quantity")
    min_notional = Column(String(50), nullable=True, comment="Minimum order notional value")
    tick_size = Column(String(50), nullable=True, comment="Minimum price increment")
    step_size = Column(String(50), nullable=True, comment="Minimum quantity increment")
    
    # Relationships
    exchange = relationship("ExchangeModel", back_populates="symbols")
