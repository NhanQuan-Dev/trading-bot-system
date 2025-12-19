"""Risk entities module."""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional, List
import uuid

from ..enums import RiskLimitType, RiskStatus
from ..value_objects import RiskThreshold, LimitViolation


@dataclass
class RiskLimit:
    """Entity representing a risk limit configuration."""
    
    id: uuid.UUID
    user_id: uuid.UUID
    limit_type: RiskLimitType
    limit_value: Decimal
    symbol: Optional[str]  # None for global limits
    enabled: bool
    threshold: RiskThreshold
    created_at: datetime
    updated_at: datetime
    violations: List[LimitViolation] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate risk limit."""
        if self.limit_value <= 0:
            raise ValueError("Limit value must be positive")
    
    def check_violation(self, current_value: Decimal) -> Optional[LimitViolation]:
        """Check if current value violates this limit."""
        if not self.enabled:
            return None
            
        if current_value <= self.limit_value:
            return None
        
        violation_percentage = (current_value / self.limit_value) * 100
        
        violation = LimitViolation(
            limit_type=self.limit_type.value,
            current_value=current_value,
            limit_value=self.limit_value,
            violation_percentage=violation_percentage,
            symbol=self.symbol
        )
        
        # Add to violations history
        self.violations.append(violation)
        
        return violation
    
    def update_limit(self, new_value: Decimal) -> None:
        """Update the limit value."""
        if new_value <= 0:
            raise ValueError("Limit value must be positive")
        
        self.limit_value = new_value
        self.updated_at = datetime.utcnow()
    
    def enable(self) -> None:
        """Enable this risk limit."""
        self.enabled = True
        self.updated_at = datetime.utcnow()
    
    def disable(self) -> None:
        """Disable this risk limit."""
        self.enabled = False
        self.updated_at = datetime.utcnow()
    
    def update_threshold(self, threshold: RiskThreshold) -> None:
        """Update risk thresholds."""
        self.threshold = threshold
        self.updated_at = datetime.utcnow()


@dataclass
class RiskAlert:
    """Entity representing a risk alert/notification."""
    
    id: uuid.UUID
    user_id: uuid.UUID
    risk_limit_id: uuid.UUID
    alert_type: str
    message: str
    severity: RiskStatus
    symbol: Optional[str]
    current_value: Decimal
    limit_value: Decimal
    violation_percentage: Decimal
    acknowledged: bool
    created_at: datetime
    acknowledged_at: Optional[datetime] = None
    
    def acknowledge(self) -> None:
        """Mark this alert as acknowledged."""
        self.acknowledged = True
        self.acknowledged_at = datetime.utcnow()
    
    @property
    def is_critical(self) -> bool:
        """Check if this is a critical alert."""
        return self.severity in [RiskStatus.CRITICAL, RiskStatus.BREACHED]
