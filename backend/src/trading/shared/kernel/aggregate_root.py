"""
Base AggregateRoot class for DDD
"""

from typing import List
from .entity import Entity
from .domain_event import DomainEvent


class AggregateRoot(Entity):
    """
    Base class for aggregate roots
    
    An aggregate root is an entity that acts as the entry point to an aggregate.
    It enforces invariants and coordinates changes across entities within the aggregate.
    """
    
    def __init__(self, id: str | None = None):
        super().__init__(id)
        self._domain_events: List[DomainEvent] = []
    
    def add_domain_event(self, event: DomainEvent) -> None:
        """Add a domain event to be published"""
        self._domain_events.append(event)
    
    def get_domain_events(self) -> List[DomainEvent]:
        """Get all pending domain events"""
        return self._domain_events.copy()
    
    def clear_domain_events(self) -> None:
        """Clear all domain events after publishing"""
        self._domain_events.clear()
    
    @property
    def domain_events(self) -> List[DomainEvent]:
        """Get all pending domain events (for testing/inspection)"""
        return self._domain_events.copy()
    
    @property
    def has_domain_events(self) -> bool:
        """Check if there are pending domain events"""
        return len(self._domain_events) > 0
