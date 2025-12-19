"""Margin Call Event."""
from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime, timezone
import uuid


@dataclass(frozen=True)
class MarginCallEvent:
    """Event raised when position is near liquidation."""
    event_id: uuid.UUID
    occurred_at: datetime
    position_id: uuid.UUID
    user_id: uuid.UUID
    symbol: str
    current_price: Decimal
    liquidation_price: Decimal
    margin_ratio: Decimal
    unrealized_pnl: Decimal
    warning_level: str  # "warning", "critical", "emergency"
    
    def __post_init__(self):
        if not self.event_id:
            object.__setattr__(self, 'event_id', uuid.uuid4())
        if not self.occurred_at:
            object.__setattr__(self, 'occurred_at', datetime.now(timezone.utc))
