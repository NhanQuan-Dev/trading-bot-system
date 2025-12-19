"""Position opened domain event"""
from dataclasses import dataclass
from decimal import Decimal
from src.trading.shared.kernel.domain_event import DomainEvent


@dataclass(frozen=True)
class PositionOpenedEvent(DomainEvent):
    """
    Event emitted when a new position is opened.
    
    Attributes:
        account_id: Account identifier
        position_id: Position identifier
        symbol: Trading pair symbol
        side: Position side (LONG/SHORT)
        quantity: Position size
        entry_price: Entry price
        leverage: Position leverage
        margin_used: Margin used for position
    """
    
    account_id: str
    position_id: str
    symbol: str
    side: str
    quantity: Decimal
    entry_price: Decimal
    leverage: int
    margin_used: Decimal
    
    def __post_init__(self):
        object.__setattr__(self, 'event_id', str(__import__('uuid').uuid4()))
        object.__setattr__(self, 'occurred_at', __import__('datetime').datetime.utcnow())
