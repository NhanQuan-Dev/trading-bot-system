"""Backtesting enums."""

from enum import Enum


class BacktestStatus(str, Enum):
    """Backtest run status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BacktestMode(str, Enum):
    """Backtesting execution mode."""
    VECTORIZED = "vectorized"   # Fast vectorized backtesting
    EVENT_DRIVEN = "event_driven"  # Accurate event-by-event simulation
    TICK_BY_TICK = "tick_by_tick"  # Highest accuracy, slowest


class SlippageModel(str, Enum):
    """Slippage simulation model."""
    NONE = "none"  # No slippage
    FIXED = "fixed"  # Fixed percentage/amount
    VOLUME_BASED = "volume_based"  # Based on order size vs volume
    SPREAD_BASED = "spread_based"  # Based on bid-ask spread


class CommissionModel(str, Enum):
    """Commission calculation model."""
    NONE = "none"
    FIXED_RATE = "fixed_rate"  # Fixed percentage
    TIERED = "tiered"  # Volume-based tiers
    MAKER_TAKER = "maker_taker"  # Different for maker/taker


class PositionSizing(str, Enum):
    """Position sizing method."""
    FIXED_SIZE = "fixed_size"  # Fixed contract/shares
    FIXED_VALUE = "fixed_value"  # Fixed dollar value
    PERCENT_EQUITY = "percent_equity"  # Percentage of equity
    KELLY = "kelly"  # Kelly criterion
    VOLATILITY_BASED = "volatility_based"  # Based on volatility


class TradeDirection(str, Enum):
    """Trade direction."""
    LONG = "LONG"
    SHORT = "SHORT"


class ExitReason(str, Enum):
    """Reason for exiting a trade."""
    SIGNAL = "signal"  # Strategy signal
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"
    TRAILING_STOP = "trailing_stop"
    TIME_EXIT = "time_exit"
    END_OF_DATA = "end_of_data"
    MANUAL = "manual"
    MARGIN_CALL = "margin_call"
