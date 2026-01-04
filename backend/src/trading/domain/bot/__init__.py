"""Bot domain models for trading automation."""
from dataclasses import dataclass, field
from datetime import datetime as dt, timezone as dt_timezone
from enum import Enum
from typing import Optional, Dict, Any, List
from decimal import Decimal
import uuid


class BotStatus(str, Enum):
    """Bot status enumeration.
    
    Simplified to 3 core states:
    - RUNNING: Bot is active and can trade
    - PAUSED: Bot is paused (also used as initial/default state)
    - ERROR: Bot encountered an error
    """
    RUNNING = "RUNNING"  # Bot is running and can trade
    PAUSED = "PAUSED"    # Bot is paused (default state)
    ERROR = "ERROR"      # Bot encountered error


class StrategyType(str, Enum):
    """Strategy type enumeration."""
    GRID = "GRID"                    # Grid trading
    DCA = "DCA"                      # Dollar cost averaging
    MARTINGALE = "MARTINGALE"        # Martingale strategy  
    TREND_FOLLOWING = "TREND_FOLLOWING"  # Trend following
    MEAN_REVERSION = "MEAN_REVERSION"    # Mean reversion
    ARBITRAGE = "ARBITRAGE"          # Arbitrage
    CUSTOM = "CUSTOM"                # Custom strategy

BotType = StrategyType


class RiskLevel(str, Enum):
    """Risk level enumeration."""
    CONSERVATIVE = "CONSERVATIVE"
    MODERATE = "MODERATE"
    AGGRESSIVE = "AGGRESSIVE"
    EXTREME = "EXTREME"


@dataclass(frozen=True)
class BotConfiguration:
    """Bot configuration value object."""
    symbol: str
    base_quantity: Decimal
    quote_quantity: Decimal
    max_active_orders: int
    risk_percentage: Decimal  # Max % of balance to risk
    take_profit_percentage: Decimal
    stop_loss_percentage: Decimal
    
    # Strategy specific settings
    strategy_settings: Dict[str, Any] = field(default_factory=dict)
    
    # Risk management
    max_daily_loss: Optional[Decimal] = None
    max_drawdown: Optional[Decimal] = None
    bot_type: Optional["BotType"] = None
    
    def __post_init__(self):
        if self.base_quantity <= 0 and self.quote_quantity <= 0:
            raise ValueError("Either base quantity or quote quantity must be positive")
        # if self.base_quantity <= 0:   <-- Removed strict check
        #     raise ValueError("Base quantity must be positive")
        # if self.quote_quantity <= 0:  <-- Removed strict check
        #     raise ValueError("Quote quantity must be positive")
        if self.max_active_orders <= 0:
            raise ValueError("Max active orders must be positive")
        if not (0 < self.risk_percentage <= 100):
            raise ValueError("Risk percentage must be between 0 and 100")
        if self.take_profit_percentage <= 0:
            raise ValueError("Take profit percentage must be positive")
        if self.stop_loss_percentage <= 0:
            raise ValueError("Stop loss percentage must be positive")


@dataclass(frozen=True)
class StrategyParameters:
    """Strategy parameters value object."""
    strategy_type: StrategyType
    name: str
    description: str
    parameters: Dict[str, Any]
    
    def __post_init__(self):
        if not self.name.strip():
            raise ValueError("Strategy name cannot be empty")
        # Parameters can be empty - they will be configured in strategy file


@dataclass(frozen=True)
class BotPerformance:
    """Bot performance metrics value object."""
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_profit_loss: Decimal = Decimal("0")
    total_fees: Decimal = Decimal("0")
    max_drawdown: Decimal = Decimal("0")
    sharpe_ratio: Optional[Decimal] = None
    
    @property
    def win_rate(self) -> float:
        """Calculate win rate percentage."""
        if self.total_trades == 0:
            return 0.0
        return (self.winning_trades / self.total_trades) * 100
    
    @property
    def net_profit_loss(self) -> Decimal:
        """Calculate net P&L after fees."""
        return self.total_profit_loss - self.total_fees
    
    @property
    def average_profit_per_trade(self) -> Decimal:
        """Calculate average profit per trade."""
        if self.total_trades == 0:
            return Decimal("0")
        return self.net_profit_loss / self.total_trades


@dataclass
class Strategy:
    """Strategy entity."""
    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    strategy_type: StrategyType
    description: str
    parameters: StrategyParameters
    is_active: bool
    created_at: dt
    updated_at: dt
    
    # Performance tracking
    backtest_results: Optional[Dict[str, Any]] = None
    live_performance: BotPerformance = field(default_factory=BotPerformance)
    
    @classmethod
    def create(
        cls,
        user_id: uuid.UUID,
        name: str,
        strategy_type: StrategyType,
        description: str,
        parameters: Dict[str, Any]
    ) -> "Strategy":
        """Create a new strategy."""
        now = dt.now(dt_timezone.utc)
        strategy_params = StrategyParameters(
            strategy_type=strategy_type,
            name=name,
            description=description,
            parameters=parameters
        )
        
        return cls(
            id=uuid.uuid4(),
            user_id=user_id,
            name=name,
            strategy_type=strategy_type,
            description=description,
            parameters=strategy_params,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
    
    def update_parameters(self, parameters: Dict[str, Any]) -> None:
        """Update strategy parameters."""
        self.parameters = StrategyParameters(
            strategy_type=self.strategy_type,
            name=self.name,
            description=self.description,
            parameters=parameters
        )
        self.updated_at = dt.now(dt_timezone.utc)
    
    def activate(self) -> None:
        """Activate the strategy."""
        self.is_active = True
        self.updated_at = dt.now(dt_timezone.utc)
    
    def deactivate(self) -> None:
        """Deactivate the strategy."""
        self.is_active = False
        self.updated_at = dt.now(dt_timezone.utc)


@dataclass
class Bot:
    """Bot entity - represents a trading bot instance."""
    # Required fields
    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    strategy_id: uuid.UUID
    exchange_connection_id: uuid.UUID
    status: BotStatus
    configuration: BotConfiguration
    created_at: dt
    updated_at: dt
    
    # Optional fields
    description: Optional[str] = None
    risk_level: RiskLevel = RiskLevel.MODERATE
    
    # Runtime fields
    start_time: Optional[dt] = None
    stop_time: Optional[dt] = None
    last_error: Optional[str] = None
    
    # Performance tracking (legacy JSON-based)
    performance: BotPerformance = field(default_factory=BotPerformance)
    
    # Operational data
    active_orders: List[uuid.UUID] = field(default_factory=list)
    daily_pnl: Decimal = Decimal("0")
    total_runtime_seconds: int = 0
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # === NEW: Cumulative Stats (from DB columns) ===
    total_pnl: Decimal = Decimal("0")
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    
    # === NEW: Streak Tracking ===
    current_win_streak: int = 0
    current_loss_streak: int = 0
    max_win_streak: int = 0
    max_loss_streak: int = 0
    
    @property
    def win_rate(self) -> float:
        """Calculate win rate percentage (0-100)."""
        if self.total_trades == 0:
            return 0.0
        return round((self.winning_trades / self.total_trades) * 100, 2)
    
    @classmethod
    def create(
        cls,
        user_id: uuid.UUID,
        name: str,
        strategy_id: uuid.UUID,
        exchange_connection_id: uuid.UUID,
        configuration: BotConfiguration,
        description: Optional[str] = None,
        risk_level: RiskLevel = RiskLevel.MODERATE,
    ) -> "Bot":
        """Create a new bot."""
        now = dt.now(dt_timezone.utc)
        
        return cls(
            id=uuid.uuid4(),
            user_id=user_id,
            name=name,
            strategy_id=strategy_id,
            exchange_connection_id=exchange_connection_id,
            status=BotStatus.PAUSED,  # Default state is PAUSED
            configuration=configuration,
            description=description,
            risk_level=risk_level,
            created_at=now,
            updated_at=now,
        )
    
    def start(self) -> None:
        """Start the bot."""
        if self.status == BotStatus.RUNNING:
            raise ValueError(f"Cannot start bot in {self.status} status")
        
        self.status = BotStatus.RUNNING
        if not self.start_time:  # Only set if not already set (for retry)
            self.start_time = dt.now(dt_timezone.utc)
        self.updated_at = dt.now(dt_timezone.utc)
        self.last_error = None
    
    def mark_active(self) -> None:
        """Mark bot as successfully started and active (alias for compatibility)."""
        if self.status != BotStatus.RUNNING:
            self.status = BotStatus.RUNNING
        self.updated_at = dt.now(dt_timezone.utc)
    
    def pause(self, reason: Optional[str] = None) -> None:
        """Pause the bot."""
        if self.status != BotStatus.RUNNING:
            raise ValueError(f"Cannot pause bot in {self.status} status")
        
        self.status = BotStatus.PAUSED
        self.updated_at = dt.now(dt_timezone.utc)
        if reason:
            self.metadata["pause_reason"] = reason
    
    def resume(self) -> None:
        """Resume the bot from paused state (alias for start)."""
        if self.status != BotStatus.PAUSED:
            raise ValueError(f"Cannot resume bot in {self.status} status")
        
        self.status = BotStatus.RUNNING
        self.updated_at = dt.now(dt_timezone.utc)
        if "pause_reason" in self.metadata:
            del self.metadata["pause_reason"]
    
    def stop(self, reason: Optional[str] = None) -> None:
        """Stop the bot (transitions to PAUSED state)."""
        if self.status == BotStatus.PAUSED:
            return  # Already paused, no-op
        
        self.status = BotStatus.PAUSED
        self.stop_time = dt.now(dt_timezone.utc)
        self.updated_at = dt.now(dt_timezone.utc)
        if reason:
            self.metadata["stop_reason"] = reason
    
    def mark_stopped(self) -> None:
        """Mark bot as stopped (transitions to PAUSED state)."""
        self.status = BotStatus.PAUSED
        self.active_orders.clear()
        self.updated_at = dt.now(dt_timezone.utc)
    
    def mark_error(self, error_message: str) -> None:
        """Mark bot as having an error."""
        self.status = BotStatus.ERROR
        self.last_error = error_message
        self.stop_time = dt.now(dt_timezone.utc)
        self.updated_at = dt.now(dt_timezone.utc)
    
    def update_configuration(self, configuration: BotConfiguration) -> None:
        """Update bot configuration (only when stopped)."""
        if self.status != BotStatus.PAUSED:
            raise ValueError("Can only update configuration when bot is paused")
        
        self.configuration = configuration
        self.updated_at = dt.now(dt_timezone.utc)
    
    def add_active_order(self, order_id: uuid.UUID) -> None:
        """Add an active order."""
        if order_id not in self.active_orders:
            self.active_orders.append(order_id)
            self.updated_at = dt.now(dt_timezone.utc)
    
    def remove_active_order(self, order_id: uuid.UUID) -> None:
        """Remove an active order."""
        if order_id in self.active_orders:
            self.active_orders.remove(order_id)
            self.updated_at = dt.now(dt_timezone.utc)
    
    def update_performance(self, performance: BotPerformance) -> None:
        """Update bot performance metrics."""
        self.performance = performance
        self.updated_at = dt.now(dt_timezone.utc)
    
    def is_active(self) -> bool:
        """Check if bot is in running state."""
        return self.status == BotStatus.RUNNING
    
    def is_stopped(self) -> bool:
        """Check if bot is paused (stopped)."""
        return self.status == BotStatus.PAUSED
    
    def can_be_started(self) -> bool:
        """Check if bot can be started."""
        return self.status in [BotStatus.PAUSED, BotStatus.ERROR]
    
    def can_be_stopped(self) -> bool:
        """Check if bot can be stopped (paused)."""
        return self.status == BotStatus.RUNNING
    
    def get_runtime_seconds(self) -> int:
        """Get current runtime in seconds."""
        if not self.start_time:
            return 0
        
        start = self.start_time
        if isinstance(start, str):
            start = dt.fromisoformat(start)
        if start.tzinfo is None:
            start = start.replace(tzinfo=dt_timezone.utc)
            
        stop = self.stop_time
        if stop:
            if isinstance(stop, str):
                stop = dt.fromisoformat(stop)
            if stop.tzinfo is None:
                stop = stop.replace(tzinfo=dt_timezone.utc)
        
        if self.status in [BotStatus.RUNNING, BotStatus.PAUSED]:
            return int((dt.now(dt_timezone.utc) - start).total_seconds())
        elif stop:
            return int((stop - start).total_seconds())
        
        return 0


__all__ = [
    "BotStatus",
    "StrategyType", 
    "RiskLevel",
    "BotConfiguration",
    "StrategyParameters",
    "BotPerformance",
    "Strategy",
    "Bot",
    "BotType",
]
