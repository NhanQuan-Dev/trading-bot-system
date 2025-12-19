"""
DomainEventBus interface for DDD
"""

from abc import ABC, abstractmethod
from typing import Callable, Type
from .domain_event import DomainEvent


class DomainEventBus(ABC):
    """
    Interface for domain event bus
    
    The event bus is responsible for publishing domain events to registered handlers.
    """
    
    @abstractmethod
    def publish(self, event: DomainEvent) -> None:
        """Publish a domain event"""
        pass
    
    @abstractmethod
    def subscribe(
        self, 
        event_type: Type[DomainEvent], 
        handler: Callable[[DomainEvent], None]
    ) -> None:
        """Subscribe a handler to an event type"""
        pass
    
    @abstractmethod
    def unsubscribe(
        self, 
        event_type: Type[DomainEvent], 
        handler: Callable[[DomainEvent], None]
    ) -> None:
        """Unsubscribe a handler from an event type"""
        pass
