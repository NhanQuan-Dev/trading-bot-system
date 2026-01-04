"""SQLAlchemy models for bot and strategy tables."""
from sqlalchemy import Column, String, Integer, ForeignKey, Index, CheckConstraint, Boolean, Date, DECIMAL, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from decimal import Decimal

from .base import TimestampMixin, SoftDeleteMixin, UUIDPrimaryKeyMixin
from ..database import Base

# Cross-database JSON type (JSONB for PostgreSQL, JSON for SQLite)
JSONType = JSON().with_variant(JSONB(), "postgresql")


class BotModel(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """Trading bot model."""
    
    __tablename__ = "bots"
    __table_args__ = (
        Index('idx_bots_user_status', 'user_id', 'status'),
        Index('idx_bots_strategy_id', 'strategy_id'),
        Index('idx_bots_api_connection_id', 'exchange_connection_id'),
        Index('idx_bots_start_time', 'start_time'),
        Index('idx_bots_deleted_at', 'deleted_at'),
        Index('idx_bots_total_pnl', 'total_pnl'),  # New: for sorting by P&L
        CheckConstraint("status IN ('RUNNING', 'PAUSED', 'ERROR')", name='ck_bots_status'),
        CheckConstraint("risk_level IN ('CONSERVATIVE', 'MODERATE', 'AGGRESSIVE', 'EXTREME')", name='ck_bots_risk_level'),
        {'comment': 'Trading bots with strategy execution'}
    )
    
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    strategy_id = Column(UUID(as_uuid=True), ForeignKey('strategies.id', ondelete='RESTRICT'), nullable=False)
    exchange_connection_id = Column(UUID(as_uuid=True), ForeignKey('api_connections.id', ondelete='RESTRICT'), nullable=False)
    
    name = Column(String(100), nullable=False, comment="Bot name (user-defined)")
    description = Column(String(500), nullable=True, comment="Bot description")
    status = Column(String(20), nullable=False, default="PAUSED", comment="Bot status")
    risk_level = Column(String(20), nullable=False, default="MODERATE", comment="Risk level")
    
    # Configuration (JSONB)
    configuration = Column(JSONType, nullable=False, default={}, comment="Bot configuration JSON")
    
    # Runtime tracking
    start_time = Column(TimestampMixin.created_at.type, nullable=True, comment="Bot start timestamp")
    stop_time = Column(TimestampMixin.created_at.type, nullable=True, comment="Bot stop timestamp")
    last_error = Column(String(1000), nullable=True, comment="Last error message")
    
    # Performance tracking (JSONB)
    performance = Column(JSONType, nullable=False, default={}, comment="Performance metrics JSON")
    
    # Operational data
    active_orders = Column(JSONType, nullable=False, default=[], comment="Active order IDs JSON array")
    daily_pnl = Column(DECIMAL(20, 8), nullable=False, default=Decimal("0"), comment="Daily P&L")
    total_runtime_seconds = Column(Integer, nullable=False, default=0, comment="Total runtime in seconds")
    
    # === NEW: Cumulative Bot Stats (updated on each trade close) ===
    total_pnl = Column(DECIMAL(20, 8), nullable=False, default=Decimal("0"), comment="Total realized P&L from all closed trades")
    total_trades = Column(Integer, nullable=False, default=0, comment="Total number of closed trades")
    winning_trades = Column(Integer, nullable=False, default=0, comment="Number of winning trades (P&L > 0)")
    losing_trades = Column(Integer, nullable=False, default=0, comment="Number of losing trades (P&L < 0)")
    
    # === NEW: Streak Tracking ===
    current_win_streak = Column(Integer, nullable=False, default=0, comment="Current consecutive winning trades")
    current_loss_streak = Column(Integer, nullable=False, default=0, comment="Current consecutive losing trades")
    max_win_streak = Column(Integer, nullable=False, default=0, comment="Maximum win streak ever achieved")
    max_loss_streak = Column(Integer, nullable=False, default=0, comment="Maximum loss streak ever experienced")
    
    # Metadata
    meta_data = Column(JSONType, nullable=False, default={}, comment="Additional metadata JSON")
    
    # Relationships
    user = relationship("UserModel", back_populates="bots")
    strategy = relationship("StrategyModel", back_populates="bots")
    exchange_connection = relationship("APIConnectionModel", back_populates="bots")
    orders = relationship("OrderModel", back_populates="bot")
    positions = relationship("PositionModel", back_populates="bot")
    backtests = relationship("BacktestModel", back_populates="bot")
    bot_performance = relationship("BotPerformanceModel", back_populates="bot")


class StrategyModel(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """Trading strategy model."""
    
    __tablename__ = "strategies"
    __table_args__ = (
        Index('idx_strategies_user_type', 'user_id', 'strategy_type'),
        Index('idx_strategies_is_active', 'is_active'),
        Index('idx_strategies_deleted_at', 'deleted_at'),
        CheckConstraint("strategy_type IN ('GRID', 'DCA', 'MARTINGALE', 'TREND_FOLLOWING', 'MEAN_REVERSION', 'ARBITRAGE', 'CUSTOM')", name='ck_strategies_type'),
        {'comment': 'Trading strategies (reusable across bots)'}
    )
    
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    
    name = Column(String(100), nullable=False, comment="Strategy name")
    strategy_type = Column(String(20), nullable=False, comment="Strategy type")
    description = Column(String(1000), nullable=False, comment="Strategy description")
    parameters = Column(JSONType, nullable=False, default={}, comment="Strategy parameters JSON")
    is_active = Column(Boolean, nullable=False, default=True, comment="Is strategy active")
    
    # Performance tracking
    backtest_results = Column(JSONType, nullable=True, comment="Backtest results JSON")
    live_performance = Column(JSONType, nullable=False, default={}, comment="Live performance metrics JSON")
    
    # Relationships
    user = relationship("UserModel", back_populates="strategies")
    bots = relationship("BotModel", back_populates="strategy")
    backtests = relationship("BacktestModel", back_populates="strategy")


class BacktestModel(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """Backtest result model."""
    
    __tablename__ = "backtests"
    __table_args__ = (
        Index('idx_backtests_strategy_created', 'strategy_id', 'created_at'),
        Index('idx_backtests_bot_created', 'bot_id', 'created_at'),
        Index('idx_backtests_deleted_at', 'deleted_at'),
        CheckConstraint("timeframe IN ('1m', '5m', '15m', '1h', '4h', '1d')", name='ck_backtests_timeframe'),
        {'comment': 'Backtest results and performance metrics'}
    )
    
    strategy_id = Column(UUID(as_uuid=True), ForeignKey('strategies.id', ondelete='CASCADE'), nullable=False)
    bot_id = Column(UUID(as_uuid=True), ForeignKey('bots.id', ondelete='SET NULL'), nullable=True, comment="Bot used for backtest")
    
    # Backtest configuration
    symbol = Column(String(20), nullable=False, comment="Symbol tested")
    timeframe = Column(String(10), nullable=False, comment="Timeframe")
    start_date = Column(Date, nullable=False, comment="Backtest start date")
    end_date = Column(Date, nullable=False, comment="Backtest end date")
    initial_capital = Column(DECIMAL(20, 8), nullable=False, comment="Initial capital")
    
    # Results
    final_equity = Column(DECIMAL(20, 8), nullable=False, comment="Final equity")
    total_trades = Column(Integer, nullable=False, default=0, comment="Total number of trades")
    winning_trades = Column(Integer, nullable=False, default=0, comment="Number of winning trades")
    losing_trades = Column(Integer, nullable=False, default=0, comment="Number of losing trades")
    win_rate = Column(DECIMAL(5, 2), nullable=True, comment="Win rate percentage")
    
    # Performance metrics
    sharpe_ratio = Column(DECIMAL(10, 4), nullable=True, comment="Sharpe ratio")
    sortino_ratio = Column(DECIMAL(10, 4), nullable=True, comment="Sortino ratio")
    max_drawdown = Column(DECIMAL(10, 4), nullable=True, comment="Maximum drawdown")
    max_drawdown_percent = Column(DECIMAL(5, 2), nullable=True, comment="Max drawdown %")
    profit_factor = Column(DECIMAL(10, 4), nullable=True, comment="Profit factor")
    avg_win = Column(DECIMAL(20, 8), nullable=True, comment="Average winning trade")
    avg_loss = Column(DECIMAL(20, 8), nullable=True, comment="Average losing trade")
    total_return = Column(DECIMAL(10, 4), nullable=True, comment="Total return")
    total_return_percent = Column(DECIMAL(10, 2), nullable=True, comment="Total return %")
    
    # Additional data
    equity_curve = Column(JSONType, nullable=True, default=[], comment="Equity curve time series")
    trade_log = Column(JSONType, nullable=True, default=[], comment="Trade log details")
    meta_data = Column(JSONType, nullable=True, default={}, comment="Additional metadata")
    
    # Relationships
    strategy = relationship("StrategyModel", back_populates="backtests")
    bot = relationship("BotModel", back_populates="backtests")


class BotPerformanceModel(Base, TimestampMixin):
    """Bot daily performance tracking (analytics, no soft delete)."""
    
    __tablename__ = "bot_performance"
    __table_args__ = (
        Index('idx_bot_performance_bot_date', 'bot_id', 'date', unique=True),
        {'comment': 'Bot daily performance metrics (partitioned by date quarterly)'}
    )
    
    id = Column(Integer, primary_key=True, autoincrement=True, comment="Auto-increment ID")
    bot_id = Column(UUID(as_uuid=True), ForeignKey('bots.id', ondelete='CASCADE'), nullable=False)
    
    date = Column(Date, nullable=False, comment="Performance date")
    trades_count = Column(Integer, nullable=False, default=0, comment="Number of trades")
    winning_trades = Column(Integer, nullable=False, default=0, comment="Winning trades")
    losing_trades = Column(Integer, nullable=False, default=0, comment="Losing trades")
    
    # P&L
    daily_pnl = Column(DECIMAL(20, 8), nullable=False, default=Decimal("0"), comment="Daily P&L")
    cumulative_pnl = Column(DECIMAL(20, 8), nullable=False, default=Decimal("0"), comment="Cumulative P&L")
    win_rate = Column(DECIMAL(5, 2), nullable=True, comment="Daily win rate %")
    
    # Metrics
    sharpe_ratio = Column(DECIMAL(10, 4), nullable=True, comment="Daily Sharpe ratio")
    max_drawdown = Column(DECIMAL(10, 4), nullable=True, comment="Current max drawdown")
    volatility = Column(DECIMAL(10, 4), nullable=True, comment="Daily volatility")
    
    # Volume
    volume_traded = Column(DECIMAL(20, 8), nullable=False, default=Decimal("0"), comment="Volume traded")
    fees_paid = Column(DECIMAL(20, 8), nullable=False, default=Decimal("0"), comment="Fees paid")
    
    # Relationships
    bot = relationship("BotModel", back_populates="bot_performance")
