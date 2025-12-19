"""Position closed domain event"""
from dataclasses import dataclass
from decimal import Decimal
from src.trading.shared.kernel.domain_event import DomainEvent


@dataclass(frozen=True)
class PositionClosedEvent(DomainEvent):
    """
    Event emitted when a position is closed.
    
    Attributes:
        account_id: Account identifier
        position_id: Position identifier
        symbol: Trading pair symbol
        side: Position side (LONG/SHORT)
        quantity: Position size that was closed
        entry_price: Original entry price
        exit_price: Exit price
        realized_pnl: Realized profit/loss
        margin_released: Margin released back
    """
    
    account_id: str
    position_id: str
    symbol: str
    side: str
    quantity: Decimal
    entry_price: Decimal
    exit_price: Decimal
    realized_pnl: Decimal
    margin_released: Decimal
    
    def __post_init__(self):
        object.__setattr__(self, 'event_id', str(__import__('uuid').uuid4()))
        object.__setattr__(self, 'occurred_at', __import__('datetime').datetime.utcnow())
