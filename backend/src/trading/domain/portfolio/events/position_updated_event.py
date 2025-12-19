"""Position Updated Event."""
from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime, timezone
import uuid


@dataclass(frozen=True)
class PositionUpdatedEvent:
    """Event raised when position is updated (price, stop loss, take profit)."""
    event_id: uuid.UUID
    occurred_at: datetime
    position_id: uuid.UUID
    user_id: uuid.UUID
    symbol: str
    old_mark_price: Decimal
    new_mark_price: Decimal
    old_unrealized_pnl: Decimal
    new_unrealized_pnl: Decimal
    
    def __post_init__(self):
        if not self.event_id:
            object.__setattr__(self, 'event_id', uuid.uuid4())
        if not self.occurred_at:
            object.__setattr__(self, 'occurred_at', datetime.now(timezone.utc))
