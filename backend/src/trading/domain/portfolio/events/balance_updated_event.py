"""Balance updated domain event"""
from dataclasses import dataclass
from decimal import Decimal
from src.trading.shared.kernel.domain_event import DomainEvent


@dataclass(frozen=True)
class BalanceUpdatedEvent(DomainEvent):
    """
    Event emitted when account balance is updated.
    
    Attributes:
        account_id: Account identifier
        asset: Asset symbol
        free: New free balance
        locked: New locked balance
        old_free: Previous free balance (for auditing)
        old_locked: Previous locked balance (for auditing)
    """
    
    account_id: str
    asset: str
    free: Decimal
    locked: Decimal
    old_free: Decimal
    old_locked: Decimal
    
    def __post_init__(self):
        object.__setattr__(self, 'event_id', str(__import__('uuid').uuid4()))
        object.__setattr__(self, 'occurred_at', __import__('datetime').datetime.utcnow())
