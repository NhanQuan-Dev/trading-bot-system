"""
Base ValueObject class for DDD
"""

from abc import ABC
from typing import Any
from dataclasses import dataclass


@dataclass(frozen=True)
class ValueObject(ABC):
    """
    Base class for all value objects in the domain
    
    A value object has no identity and is defined entirely by its attributes.
    Value objects are immutable and equality is based on attribute values.
    """
    
    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, self.__class__):
            return False
        return self.__dict__ == other.__dict__
    
    def __hash__(self) -> int:
        return hash(tuple(sorted(self.__dict__.items())))
