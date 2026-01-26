"""Backtesting event types and entities."""

from enum import Enum
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID, uuid4


class BacktestEventType(str, Enum):
    """Types of events that can occur during backtesting."""
    
    # Candle events
    HTF_CANDLE_CLOSED = "htf_candle_closed"
    
    # Setup-Trigger events
    SETUP_CONFIRMED = "setup_confirmed"
    TRIGGER_HIT = "trigger_hit"
    
    # Trade lifecycle events
    TRADE_OPENED = "trade_opened"
    TRADE_CLOSED = "trade_closed"
    SCALE_IN = "scale_in"
    PARTIAL_CLOSE = "partial_close"
    LEVELS_UPDATED = "levels_updated"
    
    # Exit events
    SL_HIT = "sl_hit"
    TP_HIT = "tp_hit"
    TRAILING_STOP_UPDATED = "trailing_stop_updated"
    TRAILING_STOP_HIT = "trailing_stop_hit"
    
    # Fill events
    ORDER_FILLED = "order_filled"
    ORDER_REJECTED = "order_rejected"
    
    # Risk events
    LIQUIDATION = "liquidation"
    MARGIN_CALL = "margin_call"
    MARGIN_UPDATED = "margin_updated"


@dataclass
class BacktestEvent:
    """An event that occurred during backtesting."""
    
    id: UUID
    backtest_id: UUID
    event_type: BacktestEventType
    timestamp: datetime
    details: Dict[str, Any]
    trade_id: Optional[UUID] = None
    
    def __init__(
        self,
        backtest_id: UUID,
        event_type: BacktestEventType,
        timestamp: datetime,
        details: Dict[str, Any],
        trade_id: Optional[UUID] = None,
    ):
        self.id = uuid4()
        self.backtest_id = backtest_id
        self.event_type = event_type
        self.timestamp = timestamp
        self.details = details
        self.trade_id = trade_id
