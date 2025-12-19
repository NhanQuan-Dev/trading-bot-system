"""
Base DomainEvent class for DDD
"""

from abc import ABC
from datetime import datetime
from typing import Dict, Any
import uuid


class DomainEvent(ABC):
    """
    Base class for all domain events
    
    Domain events represent something that happened in the domain that domain experts care about.
    They should be immutable and contain all information about what happened.
    """
    
    def __init__(self):
        self.event_id = str(uuid.uuid4())
        self.occurred_at = datetime.utcnow()
    
    @property
    def event_type(self) -> str:
        """Get event type name"""
        return self.__class__.__name__
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary"""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "occurred_at": self.occurred_at.isoformat(),
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary"""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "occurred_at": self.occurred_at.isoformat(),
            "aggregate_id": self.aggregate_id,
            "aggregate_type": self.aggregate_type,
        }
