"""Equity changed domain event"""
from dataclasses import dataclass
from decimal import Decimal
from src.trading.shared.kernel.domain_event import DomainEvent


@dataclass(frozen=True)
class EquityChangedEvent(DomainEvent):
    """
    Event emitted when total equity changes significantly.
    
    Attributes:
        account_id: Account identifier
        old_equity: Previous equity value
        new_equity: New equity value
        change_percentage: Percentage change
        reason: Reason for change (e.g., "balance_update", "position_pnl")
    """
    
    account_id: str
    old_equity: Decimal
    new_equity: Decimal
    change_percentage: Decimal
    reason: str
    
    def __post_init__(self):
        object.__setattr__(self, 'event_id', str(__import__('uuid').uuid4()))
        object.__setattr__(self, 'occurred_at', __import__('datetime').datetime.utcnow())
