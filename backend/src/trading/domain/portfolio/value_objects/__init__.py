"""Portfolio domain - Value Objects."""
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Optional


class PositionSide(str, Enum):
    """Position side enumeration."""
    LONG = "LONG"
    SHORT = "SHORT"
    
    def opposite(self) -> "PositionSide":
        """Get opposite position side."""
        return PositionSide.SHORT if self == PositionSide.LONG else PositionSide.LONG
    
    def is_long(self) -> bool:
        """Check if position is long."""
        return self == PositionSide.LONG
    
    def is_short(self) -> bool:
        """Check if position is short."""
        return self == PositionSide.SHORT


class MarginMode(str, Enum):
    """Margin mode enumeration."""
    ISOLATED = "ISOLATED"
    CROSS = "CROSS"


class PositionMode(str, Enum):
    """Position mode enumeration."""
    ONE_WAY = "ONE_WAY"  # Single position per symbol
    HEDGE = "HEDGE"      # Separate long and short positions


@dataclass(frozen=True)
class AssetBalance:
    """Asset balance value object with free and locked amounts."""
    
    asset: str
    free: Decimal
    locked: Decimal
    
    def __post_init__(self):
        """Validate balance values."""
        if self.free < 0:
            raise ValueError(f"Free balance cannot be negative: {self.free}")
        if self.locked < 0:
            raise ValueError(f"Locked balance cannot be negative: {self.locked}")
    
    @property
    def total(self) -> Decimal:
        """Total balance (free + locked)."""
        return self.free + self.locked
    
    def add_free(self, amount: Decimal) -> "AssetBalance":
        """Create new balance with added free amount."""
        if amount < 0:
            raise ValueError(f"Cannot add negative amount: {amount}")
        return AssetBalance(
            asset=self.asset,
            free=self.free + amount,
            locked=self.locked
        )
    
    def subtract_free(self, amount: Decimal) -> "AssetBalance":
        """Create new balance with subtracted free amount."""
        if amount < 0:
            raise ValueError(f"Cannot subtract negative amount: {amount}")
        if self.free < amount:
            raise ValueError(f"Insufficient free balance: {self.free} < {amount}")
        return AssetBalance(
            asset=self.asset,
            free=self.free - amount,
            locked=self.locked
        )
    
    def lock(self, amount: Decimal) -> "AssetBalance":
        """Lock amount (move from free to locked)."""
        if amount < 0:
            raise ValueError(f"Cannot lock negative amount: {amount}")
        if self.free < amount:
            raise ValueError(f"Insufficient free balance to lock: {self.free} < {amount}")
        return AssetBalance(
            asset=self.asset,
            free=self.free - amount,
            locked=self.locked + amount
        )
    
    def unlock(self, amount: Decimal) -> "AssetBalance":
        """Unlock amount (move from locked to free)."""
        if amount < 0:
            raise ValueError(f"Cannot unlock negative amount: {amount}")
        if self.locked < amount:
            raise ValueError(f"Insufficient locked balance to unlock: {self.locked} < {amount}")
        return AssetBalance(
            asset=self.asset,
            free=self.free + amount,
            locked=self.locked - amount
        )


@dataclass(frozen=True)
class Leverage:
    """Leverage value object with validation."""
    
    value: int
    
    MIN_LEVERAGE = 1
    MAX_LEVERAGE = 125
    
    def __post_init__(self):
        """Validate leverage value."""
        if not self.MIN_LEVERAGE <= self.value <= self.MAX_LEVERAGE:
            raise ValueError(
                f"Leverage must be between {self.MIN_LEVERAGE} and {self.MAX_LEVERAGE}, got {self.value}"
            )
    
    @classmethod
    def from_int(cls, value: int) -> "Leverage":
        """Create leverage from integer."""
        return cls(value=value)
    
    def __int__(self) -> int:
        """Convert to integer."""
        return self.value
    
    def __str__(self) -> str:
        """String representation."""
        return f"{self.value}x"


@dataclass(frozen=True)
class PositionRisk:
    """Position risk metrics value object."""
    
    liquidation_price: Optional[Decimal]
    margin_ratio: Decimal  # Current margin / Initial margin
    unrealized_pnl: Decimal
    roe: Decimal  # Return on Equity (%)
    
    def is_liquidation_risk(self, threshold: Decimal = Decimal("0.8")) -> bool:
        """Check if position is at liquidation risk."""
        return self.margin_ratio >= threshold
    
    def distance_to_liquidation(self, current_price: Decimal) -> Optional[Decimal]:
        """Calculate price distance to liquidation in percentage."""
        if self.liquidation_price is None:
            return None
        if current_price == 0:
            return None
        return abs((self.liquidation_price - current_price) / current_price * 100)


@dataclass(frozen=True)
class PnL:
    """Profit and Loss value object."""
    
    realized: Decimal
    unrealized: Decimal
    
    @property
    def total(self) -> Decimal:
        """Total P&L."""
        return self.realized + self.unrealized
    
    def add_realized(self, amount: Decimal) -> "PnL":
        """Add to realized P&L."""
        return PnL(
            realized=self.realized + amount,
            unrealized=self.unrealized
        )
    
    def update_unrealized(self, amount: Decimal) -> "PnL":
        """Update unrealized P&L."""
        return PnL(
            realized=self.realized,
            unrealized=amount
        )
    
    def realize(self) -> "PnL":
        """Convert unrealized to realized P&L."""
        return PnL(
            realized=self.realized + self.unrealized,
            unrealized=Decimal("0")
        )
    
    def calculate_roe(self, initial_margin: Decimal) -> Decimal:
        """Calculate Return on Equity percentage."""
        if initial_margin == 0:
            return Decimal("0")
        return (self.total / initial_margin) * 100
