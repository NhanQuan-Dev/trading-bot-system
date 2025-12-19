"""Risk domain events module."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID
from typing import Optional

from ....shared.kernel.domain_event import DomainEvent


@dataclass(frozen=True)
class RiskLimitViolatedEvent(DomainEvent):
    """Domain event fired when a risk limit is violated."""
    
    user_id: UUID
    risk_limit_id: UUID
    limit_type: str
    symbol: Optional[str]
    current_value: Decimal
    limit_value: Decimal
    violation_percentage: Decimal
    severity: str
    occurred_at: datetime


@dataclass(frozen=True)
class RiskLimitCreatedEvent(DomainEvent):
    """Domain event fired when a new risk limit is created."""
    
    user_id: UUID
    risk_limit_id: UUID
    limit_type: str
    limit_value: Decimal
    symbol: Optional[str]
    created_at: datetime


@dataclass(frozen=True)
class RiskAlertCreatedEvent(DomainEvent):
    """Domain event fired when a risk alert is created."""
    
    user_id: UUID
    alert_id: UUID
    risk_limit_id: UUID
    alert_type: str
    severity: str
    symbol: Optional[str]
    created_at: datetime


@dataclass(frozen=True)
class CriticalRiskBreachEvent(DomainEvent):
    """Domain event fired when a critical risk limit is breached."""
    
    user_id: UUID
    risk_limit_id: UUID
    limit_type: str
    symbol: Optional[str]
    current_value: Decimal
    limit_value: Decimal
    violation_percentage: Decimal
    requires_immediate_action: bool
    occurred_at: datetime
