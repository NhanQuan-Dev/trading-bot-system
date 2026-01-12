"""Backtesting entities."""

from dataclasses import dataclass, field
from decimal import Decimal
from datetime import datetime, UTC
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4

from .enums import BacktestStatus, TradeDirection
from .value_objects import PerformanceMetrics, BacktestConfig, EquityCurvePoint


@dataclass
class BacktestTrade:
    """A simulated trade in a backtest."""
    
    id: UUID = field(default_factory=uuid4)
    symbol: str = ""
    direction: TradeDirection = TradeDirection.LONG
    
    # Entry
    entry_time: datetime = field(default_factory=datetime.utcnow)
    entry_price: Decimal = Decimal("0")
    entry_quantity: Decimal = Decimal("0")
    entry_commission: Decimal = Decimal("0")
    entry_slippage: Decimal = Decimal("0")
    
    # Exit
    exit_time: Optional[datetime] = None
    exit_price: Optional[Decimal] = None
    exit_quantity: Optional[Decimal] = None
    exit_commission: Decimal = Decimal("0")
    exit_slippage: Decimal = Decimal("0")
    
    # P&L
    gross_pnl: Decimal = Decimal("0")
    net_pnl: Decimal = Decimal("0")
    pnl_percent: Decimal = Decimal("0")
    
    # Risk metrics
    mae: Decimal = Decimal("0")  # Maximum Adverse Excursion
    mfe: Decimal = Decimal("0")  # Maximum Favorable Excursion
    
    # Metadata
    strategy_signal: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    notes: Optional[str] = None
    entry_reason: Optional[Dict[str, Any]] = None
    exit_reason: Optional[Dict[str, Any]] = None
    
    def close_trade(
        self,
        exit_time: datetime,
        exit_price: Decimal,
        exit_quantity: Decimal = None,
        commission: Decimal = Decimal("0"),
        slippage: Decimal = Decimal("0"),
    ):
        """Close the trade and calculate P&L."""
        self.exit_time = exit_time
        self.exit_price = exit_price
        self.exit_quantity = exit_quantity or self.entry_quantity
        self.exit_commission = commission
        self.exit_slippage = slippage
        
        # Calculate P&L
        if self.direction == TradeDirection.LONG:
            price_diff = self.exit_price - self.entry_price
        else:
            price_diff = self.entry_price - self.exit_price
        
        self.gross_pnl = price_diff * self.exit_quantity
        total_costs = (
            self.entry_commission + self.exit_commission +
            self.entry_slippage + self.exit_slippage
        )
        self.net_pnl = self.gross_pnl - total_costs
        
        # Calculate return percentage
        entry_value = self.entry_price * self.entry_quantity
        if entry_value > 0:
            self.pnl_percent = (self.net_pnl / entry_value) * Decimal("100")
    
    @property
    def is_open(self) -> bool:
        """Check if trade is still open."""
        return self.exit_time is None
    
    @property
    def is_winner(self) -> bool:
        """Check if trade is profitable."""
        return self.net_pnl > 0
    
    @property
    def duration_seconds(self) -> Optional[float]:
        """Trade duration in seconds."""
        if self.exit_time:
            return (self.exit_time - self.entry_time).total_seconds()
        return None


@dataclass
class BacktestPosition:
    """Current position state during backtest."""
    
    symbol: str
    direction: Optional[TradeDirection] = None
    quantity: Decimal = Decimal("0")
    avg_entry_price: Decimal = Decimal("0")
    unrealized_pnl: Decimal = Decimal("0")
    current_price: Decimal = Decimal("0")
    
    # Stop Loss / Take Profit
    stop_loss: Optional[Decimal] = None
    take_profit: Optional[Decimal] = None
    
    # Trailing Stop
    trailing_stop_percent: Optional[Decimal] = None  # e.g., Decimal("2.0") for 2%
    trailing_stop_price: Optional[Decimal] = None    # Current trailing stop price
    highest_price_since_entry: Optional[Decimal] = None  # For LONG: track highest
    lowest_price_since_entry: Optional[Decimal] = None   # For SHORT: track lowest
    
    # Metadata
    entry_time: Optional[str] = None
    entry_commission: Decimal = Decimal("0")
    metadata: Optional[Dict[str, Any]] = None
    
    def is_flat(self) -> bool:
        """Check if position is flat (no position)."""
        return self.quantity == 0
    
    def is_long(self) -> bool:
        """Check if long position."""
        return self.quantity > 0 and self.direction == TradeDirection.LONG
    
    def is_short(self) -> bool:
        """Check if short position."""
        return self.quantity > 0 and self.direction == TradeDirection.SHORT
    
    def update_unrealized_pnl(self, current_price: Decimal):
        """Update unrealized P&L based on current price."""
        self.current_price = current_price
        
        if self.is_flat():
            self.unrealized_pnl = Decimal("0")
            return
        
        if self.direction == TradeDirection.LONG:
            price_diff = current_price - self.avg_entry_price
        else:
            price_diff = self.avg_entry_price - current_price
        
        self.unrealized_pnl = price_diff * self.quantity
    
    def update_trailing_stop(self, candle_high: Decimal, candle_low: Decimal):
        """Update trailing stop based on new high/low prices.
        
        For LONG: Trail based on highest price, stop below
        For SHORT: Trail based on lowest price, stop above
        """
        if not self.trailing_stop_percent:
            return
        
        if self.direction == TradeDirection.LONG:
            # Track highest price
            if self.highest_price_since_entry is None:
                self.highest_price_since_entry = candle_high
            elif candle_high > self.highest_price_since_entry:
                self.highest_price_since_entry = candle_high
            
            # Update trailing stop price
            trail_distance = self.highest_price_since_entry * (self.trailing_stop_percent / Decimal("100"))
            new_trailing_stop = self.highest_price_since_entry - trail_distance
            
            # Trailing stop only moves UP (never down)
            if self.trailing_stop_price is None or new_trailing_stop > self.trailing_stop_price:
                self.trailing_stop_price = new_trailing_stop
        
        else:  # SHORT
            # Track lowest price
            if self.lowest_price_since_entry is None:
                self.lowest_price_since_entry = candle_low
            elif candle_low < self.lowest_price_since_entry:
                self.lowest_price_since_entry = candle_low
            
            # Update trailing stop price
            trail_distance = self.lowest_price_since_entry * (self.trailing_stop_percent / Decimal("100"))
            new_trailing_stop = self.lowest_price_since_entry + trail_distance
            
            # Trailing stop only moves DOWN (never up)
            if self.trailing_stop_price is None or new_trailing_stop < self.trailing_stop_price:
                self.trailing_stop_price = new_trailing_stop


@dataclass
class BacktestResults:
    """Complete results of a backtest run."""
    
    # Summary
    start_date: datetime
    end_date: datetime
    duration_days: int
    
    # Capital
    initial_capital: Decimal
    final_equity: Decimal
    peak_equity: Decimal
    
    # Performance metrics
    metrics: Optional[PerformanceMetrics] = None
    
    # Equity curve
    equity_curve: List[EquityCurvePoint] = field(default_factory=list)
    
    # Trade details
    trades: List[BacktestTrade] = field(default_factory=list)
    
    # Drawdown history
    drawdowns: List[Dict[str, Any]] = field(default_factory=list)
    
    # Monthly returns
    monthly_returns: Dict[str, Decimal] = field(default_factory=dict)
    
    # Additional statistics
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def total_return(self) -> Decimal:
        """Calculate total return percentage."""
        if self.initial_capital > 0:
            return ((self.final_equity - self.initial_capital) / 
                   self.initial_capital * Decimal("100"))
        return Decimal("0")
    
    @property
    def total_trades(self) -> int:
        """Total number of trades."""
        return len(self.trades)
    
    @property
    def winning_trades(self) -> int:
        """Number of winning trades."""
        return sum(1 for t in self.trades if t.is_winner)
    
    @property
    def losing_trades(self) -> int:
        """Number of losing trades."""
        return sum(1 for t in self.trades if not t.is_winner)
    
    @property
    def win_rate(self) -> Decimal:
        """Win rate percentage."""
        if self.total_trades > 0:
            return Decimal(self.winning_trades) / Decimal(self.total_trades) * Decimal("100")
        return Decimal("0")


@dataclass
class BacktestRun:
    """A backtest execution run."""
    
    id: UUID = field(default_factory=uuid4)
    user_id: UUID = field(default_factory=uuid4)
    
    # Configuration
    name: str = ""
    description: Optional[str] = None
    strategy_id: Optional[UUID] = None
    strategy_name: Optional[str] = None
    
    # Exchange connection - required for multi-exchange support
    exchange_connection_id: Optional[UUID] = None
    exchange_name: Optional[str] = None  # Loaded from relationship
    
    # Timeframe
    symbol: str = ""
    start_date: datetime = field(default_factory=datetime.utcnow)
    end_date: datetime = field(default_factory=datetime.utcnow)
    timeframe: str = "1h"  # Candle interval
    
    # Configuration
    config: BacktestConfig = field(default_factory=BacktestConfig)

    
    # State
    status: BacktestStatus = BacktestStatus.PENDING
    progress_percent: Decimal = Decimal("0")
    status_message: Optional[str] = None  # NEW: User-friendly progress message
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Results Summary
    final_equity: Optional[Decimal] = None
    total_trades: Optional[int] = None
    win_rate: Optional[Decimal] = None
    total_return: Optional[Decimal] = None
    
    # Performance Metrics (loaded from results)
    profit_factor: Optional[Decimal] = None
    max_drawdown: Optional[Decimal] = None
    sharpe_ratio: Optional[Decimal] = None
    
    # Detailed Results (loaded on demand)
    results: Optional[BacktestResults] = None
    error_message: Optional[str] = None
    
    @property
    def initial_capital(self) -> Decimal:
        """Get initial capital from config."""
        return self.config.initial_capital
        
    @property
    def start_time(self) -> Optional[datetime]:
        """Alias for started_at."""
        return self.started_at
        
    @property
    def end_time(self) -> Optional[datetime]:
        """Alias for completed_at."""
        return self.completed_at
    
    # Runtime state (not persisted)
    _current_equity: Decimal = field(default=Decimal("0"), init=False, repr=False)
    _current_positions: Dict[str, BacktestPosition] = field(
        default_factory=dict, init=False, repr=False
    )
    _open_trades: List[BacktestTrade] = field(
        default_factory=list, init=False, repr=False
    )
    
    def start(self):
        """Start the backtest run."""
        if self.status != BacktestStatus.PENDING:
            raise ValueError(f"Cannot start backtest in {self.status} status")
        
        self.status = BacktestStatus.RUNNING
        self.started_at = datetime.utcnow()
        self._current_equity = self.config.initial_capital
        self._current_positions = {}
        self._open_trades = []
        self.status_message = "Starting backtest..."
    
    def complete(self, results: BacktestResults):
        """Complete the backtest with results."""
        if self.status != BacktestStatus.RUNNING:
            raise ValueError(f"Cannot complete backtest in {self.status} status")
        
        self.status = BacktestStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        self.results = results
        self.progress_percent = Decimal("100")
        self.status_message = "Backtest completed"
    
    def fail(self, error: str):
        """Mark backtest as failed."""
        self.status = BacktestStatus.FAILED
        self.completed_at = datetime.utcnow()
        self.error_message = error
        self.status_message = f"Failed: {error[:100]}" if len(error) > 100 else f"Failed: {error}"
    
    def cancel(self):
        """Cancel the backtest."""
        if self.status not in [BacktestStatus.PENDING, BacktestStatus.RUNNING]:
            raise ValueError(f"Cannot cancel backtest in {self.status} status")
        
        self.status = BacktestStatus.CANCELLED
        self.completed_at = datetime.utcnow()
        self.status_message = "Backtest cancelled"
    
    def update_progress(self, percent: Decimal, message: Optional[str] = None):
        """Update backtest progress with optional status message."""
        self.progress_percent = max(Decimal("0"), min(percent, Decimal("100")))
        if message:
            self.status_message = message
    
    @property
    def is_running(self) -> bool:
        """Check if backtest is currently running."""
        return self.status == BacktestStatus.RUNNING
    
    @property
    def is_completed(self) -> bool:
        """Check if backtest completed successfully."""
        return self.status == BacktestStatus.COMPLETED
    
    @property
    def is_failed(self) -> bool:
        """Check if backtest failed."""
        return self.status == BacktestStatus.FAILED
    
    @property
    def duration_seconds(self) -> Optional[float]:
        """Backtest execution duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
