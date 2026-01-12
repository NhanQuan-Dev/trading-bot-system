"""Backtesting value objects."""

from dataclasses import dataclass, field
from decimal import Decimal
from datetime import datetime
from typing import List, Dict


@dataclass(frozen=True)
class PerformanceMetrics:
    """Comprehensive performance metrics for a backtest."""
    
    # Returns
    total_return: Decimal  # Total return percentage
    annual_return: Decimal  # Annualized return
    compound_annual_growth_rate: Decimal  # CAGR
    
    # Risk Metrics
    sharpe_ratio: Decimal  # Risk-adjusted return
    sortino_ratio: Decimal  # Downside deviation adjusted return
    calmar_ratio: Decimal  # Return / max drawdown
    max_drawdown: Decimal  # Maximum drawdown percentage
    max_drawdown_duration_days: int  # Longest drawdown period
    
    # Volatility
    volatility: Decimal  # Standard deviation of returns
    downside_deviation: Decimal  # Downside volatility
    
    # Win/Loss Statistics
    win_rate: Decimal  # Percentage of winning trades
    profit_factor: Decimal  # Gross profit / gross loss
    payoff_ratio: Decimal  # Average win / average loss
    expected_value: Decimal  # Expected value per trade
    
    # Trade Counts
    total_trades: int
    winning_trades: int
    losing_trades: int
    break_even_trades: int
    
    # Trade Amounts
    average_trade_pnl: Decimal
    average_winning_trade: Decimal
    average_losing_trade: Decimal
    largest_winning_trade: Decimal
    largest_losing_trade: Decimal
    
    # Consecutive Trades
    max_consecutive_wins: int
    max_consecutive_losses: int
    
    # Exposure
    average_exposure_percent: Decimal  # Time in market
    max_simultaneous_positions: int
    
    # Risk of Ruin
    risk_of_ruin: Decimal  # Probability of losing all capital


@dataclass(frozen=True)
class DrawdownInfo:
    """Drawdown information."""
    start_date: datetime
    end_date: datetime
    recovery_date: datetime | None
    drawdown_percent: Decimal
    drawdown_value: Decimal
    duration_days: int
    recovery_duration_days: int | None


@dataclass(frozen=True)
class TradeStatistics:
    """Statistics for a group of trades."""
    count: int
    total_pnl: Decimal
    average_pnl: Decimal
    median_pnl: Decimal
    std_dev_pnl: Decimal
    min_pnl: Decimal
    max_pnl: Decimal
    average_duration_hours: float
    average_mae: Decimal  # Maximum Adverse Excursion
    average_mfe: Decimal  # Maximum Favorable Excursion


@dataclass(frozen=True)
class TimeframeReturns:
    """Returns broken down by timeframe."""
    daily_returns: List[Decimal]
    weekly_returns: List[Decimal]
    monthly_returns: List[Decimal]
    yearly_returns: List[Decimal]
    
    # Monthly win rates
    months_with_profit: int
    months_with_loss: int
    
    # Best/worst periods
    best_day_return: Decimal
    worst_day_return: Decimal
    best_month_return: Decimal
    worst_month_return: Decimal
    best_year_return: Decimal
    worst_year_return: Decimal


@dataclass(frozen=True)
class BacktestConfig:
    """Configuration for backtest execution."""
    
    # Symbol
    symbol: str = ""
    
    # Execution mode
    mode: str = "event_driven"
    
    # Capital settings
    initial_capital: Decimal = Decimal("100000")
    allow_short_selling: bool = True
    margin_requirement: Decimal = Decimal("1.0")  # 1.0 = no margin
    
    # Costs
    slippage_model: str = "fixed"
    slippage_percent: Decimal = Decimal("0.001")  # 0.1%
    commission_model: str = "fixed_rate"
    commission_percent: Decimal = Decimal("0.001")
    
    # Advanced Fee Structure
    taker_fee_rate: Decimal = Decimal("0.0004")  # 0.04%
    maker_fee_rate: Decimal = Decimal("0.0002")  # 0.02%
    funding_rate_daily: Decimal = Decimal("0.0003") # 0.03% / day
    collect_funding_fee: bool = True
    
    # Position sizing
    position_sizing: str = "percent_equity"
    position_size_value: Decimal = Decimal("0.1")  # 10% of equity
    max_position_size: Decimal | None = None
    
    # Risk management
    leverage: int = 1
    stop_loss_percent: Decimal | None = None
    take_profit_percent: Decimal | None = None
    trailing_stop_percent: Decimal | None = None
    max_positions: int = 1
    
    # Timing
    use_market_open_prices: bool = False
    execution_delay_bars: int = 0
    
    # Spec-required: Fill policy configuration
    fill_policy: str = "optimistic"  # optimistic | neutral | strict
    price_path_assumption: str = "neutral"  # neutral | optimistic | realistic
    
    # Other
    compound_returns: bool = True
    reinvest_profits: bool = True


@dataclass(frozen=True)
class EquityCurvePoint:
    """Single point on the equity curve."""
    timestamp: datetime
    equity: Decimal
    cash: Decimal
    positions_value: Decimal
    drawdown: Decimal
    drawdown_percent: Decimal
    return_percent: Decimal
