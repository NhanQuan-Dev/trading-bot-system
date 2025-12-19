"""Risk value objects module."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional


@dataclass(frozen=True)
class RiskMetrics:
    """Value object representing current risk metrics for a user or position."""
    
    current_equity: Decimal
    daily_pnl: Decimal
    unrealized_pnl: Decimal
    realized_pnl: Decimal
    drawdown_percentage: Decimal
    margin_ratio: Decimal
    exposure_percentage: Decimal
    
    def __post_init__(self):
        """Validate risk metrics."""
        if self.current_equity < 0:
            raise ValueError("Current equity cannot be negative")
        
        if not (0 <= self.drawdown_percentage <= 100):
            raise ValueError("Drawdown percentage must be between 0 and 100")
            
        if not (0 <= self.margin_ratio <= 100):
            raise ValueError("Margin ratio must be between 0 and 100")
            
        if not (0 <= self.exposure_percentage <= 100):
            raise ValueError("Exposure percentage must be between 0 and 100")
    
    @property
    def total_pnl(self) -> Decimal:
        """Calculate total P&L (realized + unrealized)."""
        return self.realized_pnl + self.unrealized_pnl
    
    @property
    def equity_at_risk(self) -> Decimal:
        """Calculate equity at risk based on unrealized P&L."""
        return abs(self.unrealized_pnl) if self.unrealized_pnl < 0 else Decimal('0')


@dataclass(frozen=True)
class RiskThreshold:
    """Value object representing risk thresholds for alerts."""
    
    warning_threshold: Decimal  # Percentage of limit at which to warn
    critical_threshold: Decimal  # Percentage of limit at which to mark critical
    
    def __post_init__(self):
        """Validate thresholds."""
        if not (0 < self.warning_threshold <= 100):
            raise ValueError("Warning threshold must be between 0 and 100")
            
        if not (0 < self.critical_threshold <= 100):
            raise ValueError("Critical threshold must be between 0 and 100")
            
        if self.warning_threshold >= self.critical_threshold:
            raise ValueError("Warning threshold must be less than critical threshold")


@dataclass(frozen=True)
class LimitViolation:
    """Value object representing a risk limit violation."""
    
    limit_type: str
    current_value: Decimal
    limit_value: Decimal
    violation_percentage: Decimal
    symbol: Optional[str] = None
    
    @property
    def is_warning(self) -> bool:
        """Check if this is a warning level violation (>80%)."""
        return self.violation_percentage >= 80
    
    @property
    def is_critical(self) -> bool:
        """Check if this is a critical level violation (>95%)."""
        return self.violation_percentage >= 95
    
    @property
    def is_breached(self) -> bool:
        """Check if the limit is actually breached (>100%)."""
        return self.violation_percentage >= 100
