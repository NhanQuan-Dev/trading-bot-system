"""
DDD Kernel - Base classes for Domain-Driven Design
"""

from .entity import Entity
from .value_object import ValueObject
from .aggregate_root import AggregateRoot
from .domain_event import DomainEvent
from .domain_event_bus import DomainEventBus
from .repository_interface import Repository

__all__ = [
    "Entity",
    "ValueObject",
    "AggregateRoot",
    "DomainEvent",
    "DomainEventBus",
    "Repository",
]
