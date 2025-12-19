"""Backtesting models for Phase 5."""

from decimal import Decimal
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Index, CheckConstraint, Text, DECIMAL, Date, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB, ENUM as PG_ENUM
from sqlalchemy.orm import relationship
import enum

from ..database import Base
from .base import UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin

# Cross-database JSON type (JSONB for PostgreSQL, JSON for SQLite)
JSONType = JSON().with_variant(JSONB(), "postgresql")


class BacktestRunModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Backtest run tracking model (Phase 5)."""
    
    __tablename__ = "backtest_runs"
    __table_args__ = (
        Index('idx_backtest_runs_user_created', 'user_id', 'created_at'),
        Index('idx_backtest_runs_strategy', 'strategy_id'),
        Index('idx_backtest_runs_status', 'status'),
        Index('idx_backtest_runs_symbol', 'symbol'),
        {'comment': 'Backtest execution runs and progress tracking'}
    )
    
    # Ownership
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    strategy_id = Column(UUID(as_uuid=True), ForeignKey('strategies.id', ondelete='CASCADE'), nullable=False)
    
    # Configuration
    symbol = Column(String(20), nullable=False, comment="Symbol to backtest")
    timeframe = Column(String(10), nullable=False, comment="Candlestick timeframe")
    start_date = Column(Date, nullable=False, comment="Backtest start date")
    end_date = Column(Date, nullable=False, comment="Backtest end date")
    initial_capital = Column(DECIMAL(20, 8), nullable=False, comment="Initial capital")
    config = Column(JSONType, nullable=False, comment="Full backtest configuration")
    
    # Execution state
    status = Column(String(20), nullable=False, default="pending", comment="Execution status")
    progress_percent = Column(Integer, nullable=False, default=0, comment="Progress percentage")
    start_time = Column(DateTime, nullable=True, comment="Execution start time")
    end_time = Column(DateTime, nullable=True, comment="Execution end time")
    error_message = Column(Text, nullable=True, comment="Error message if failed")
    
    # Results (populated after completion)
    final_equity = Column(DECIMAL(20, 8), nullable=True, comment="Final equity")
    total_trades = Column(Integer, nullable=True, comment="Total trades executed")
    win_rate = Column(DECIMAL(5, 2), nullable=True, comment="Win rate percentage")
    total_return = Column(DECIMAL(10, 4), nullable=True, comment="Total return percentage")
    
    # Relationships
    user = relationship("UserModel", foreign_keys=[user_id])
    strategy = relationship("StrategyModel", foreign_keys=[strategy_id])
    
    # One-to-one relationship with result (access via result attribute)
    result = relationship("BacktestResultModel", back_populates="run", uselist=False)


class BacktestResultModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Backtest results and performance metrics."""
    
    __tablename__ = "backtest_results"
    __table_args__ = (
        Index('idx_backtest_results_run', 'backtest_run_id'),
        {'comment': 'Detailed backtest performance results'}
    )
    
    # Link to run
    backtest_run_id = Column(UUID(as_uuid=True), ForeignKey('backtest_runs.id', ondelete='CASCADE'), nullable=False, unique=True)
    
    # Capital tracking
    initial_capital = Column(DECIMAL(20, 8), nullable=False)
    final_equity = Column(DECIMAL(20, 8), nullable=False)
    peak_equity = Column(DECIMAL(20, 8), nullable=False)
    
    # Trade statistics
    total_trades = Column(Integer, nullable=False, default=0)
    winning_trades = Column(Integer, nullable=False, default=0)
    losing_trades = Column(Integer, nullable=False, default=0)
    break_even_trades = Column(Integer, nullable=False, default=0)
    
    # Returns
    total_return = Column(DECIMAL(10, 4), nullable=False)
    annual_return = Column(DECIMAL(10, 4), nullable=False)
    cagr = Column(DECIMAL(10, 4), nullable=False)
    
    # Risk metrics
    sharpe_ratio = Column(DECIMAL(10, 4), nullable=True)
    sortino_ratio = Column(DECIMAL(10, 4), nullable=True)
    calmar_ratio = Column(DECIMAL(10, 4), nullable=True)
    max_drawdown = Column(DECIMAL(10, 4), nullable=False)
    max_drawdown_duration_days = Column(Integer, nullable=False, default=0)
    volatility = Column(DECIMAL(10, 4), nullable=False)
    downside_deviation = Column(DECIMAL(10, 4), nullable=False)
    
    # Win/Loss statistics
    win_rate = Column(DECIMAL(5, 2), nullable=False)
    profit_factor = Column(DECIMAL(10, 4), nullable=False)
    payoff_ratio = Column(DECIMAL(10, 4), nullable=False)
    expected_value = Column(DECIMAL(20, 8), nullable=False)
    
    # Trade P&L
    average_trade_pnl = Column(DECIMAL(20, 8), nullable=False)
    average_winning_trade = Column(DECIMAL(20, 8), nullable=False)
    average_losing_trade = Column(DECIMAL(20, 8), nullable=False)
    largest_winning_trade = Column(DECIMAL(20, 8), nullable=False)
    largest_losing_trade = Column(DECIMAL(20, 8), nullable=False)
    
    # Consecutive statistics
    max_consecutive_wins = Column(Integer, nullable=False, default=0)
    max_consecutive_losses = Column(Integer, nullable=False, default=0)
    
    # Exposure
    average_exposure_percent = Column(DECIMAL(5, 2), nullable=False)
    max_simultaneous_positions = Column(Integer, nullable=False, default=1)
    
    # Additional metrics
    risk_of_ruin = Column(DECIMAL(5, 2), nullable=False)
    
    # Detailed data
    equity_curve = Column(JSONType, nullable=False, default=list, comment="Equity curve points")
    trades = Column(JSONType, nullable=False, default=list, comment="Trade details")
    monthly_returns = Column(JSONType, nullable=True, comment="Monthly returns breakdown")
    drawdowns = Column(JSONType, nullable=True, comment="Drawdown events")
    
    # Relationships
    run = relationship("BacktestRunModel", foreign_keys=[backtest_run_id], back_populates="result")


class BacktestTradeModel(Base, UUIDPrimaryKeyMixin):
    """Individual backtest trade record."""
    
    __tablename__ = "backtest_trades"
    __table_args__ = (
        Index('idx_backtest_trades_result', 'result_id'),
        Index('idx_backtest_trades_entry_time', 'entry_time'),
        {'comment': 'Individual trades from backtest execution'}
    )
    
    # Link to result
    result_id = Column(UUID(as_uuid=True), ForeignKey('backtest_results.id', ondelete='CASCADE'), nullable=False)
    
    # Trade details
    symbol = Column(String(20), nullable=False)
    direction = Column(String(10), nullable=False)  # LONG, SHORT
    entry_price = Column(DECIMAL(20, 8), nullable=False)
    exit_price = Column(DECIMAL(20, 8), nullable=False)
    quantity = Column(DECIMAL(20, 8), nullable=False)
    
    # Timing
    entry_time = Column(DateTime, nullable=False)
    exit_time = Column(DateTime, nullable=False)
    duration_seconds = Column(Integer, nullable=True)
    
    # P&L
    gross_pnl = Column(DECIMAL(20, 8), nullable=False)
    commission = Column(DECIMAL(20, 8), nullable=False, default=0)
    slippage = Column(DECIMAL(20, 8), nullable=False, default=0)
    net_pnl = Column(DECIMAL(20, 8), nullable=False)
    pnl_percent = Column(DECIMAL(10, 4), nullable=False)
    
    # Additional metrics
    mae = Column(DECIMAL(20, 8), nullable=True, comment="Maximum Adverse Excursion")
    mfe = Column(DECIMAL(20, 8), nullable=True, comment="Maximum Favorable Excursion")
    
    # Relationship
    result = relationship("BacktestResultModel", foreign_keys=[result_id])
