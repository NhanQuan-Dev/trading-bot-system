"""
Base Entity class for DDD
"""

from abc import ABC
from typing import Any
from datetime import datetime
import uuid


class Entity(ABC):
    """
    Base class for all entities in the domain
    
    An entity is defined by its identity, not its attributes.
    Two entities with the same ID are considered equal even if their attributes differ.
    """
    
    def __init__(self, id: str | None = None):
        self._id = id or str(uuid.uuid4())
        self._created_at = datetime.utcnow()
        self._updated_at = datetime.utcnow()
    
    @property
    def id(self) -> str:
        """Entity unique identifier"""
        return self._id
    
    @property
    def created_at(self) -> datetime:
        """When the entity was created"""
        return self._created_at
    
    @property
    def updated_at(self) -> datetime:
        """When the entity was last updated"""
        return self._updated_at
    
    def _mark_updated(self) -> None:
        """Mark entity as updated"""
        self._updated_at = datetime.utcnow()
    
    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Entity):
            return False
        return self.id == other.id
    
    def __hash__(self) -> int:
        return hash(self.id)
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id={self.id})"
