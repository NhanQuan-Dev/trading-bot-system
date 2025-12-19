"""
Repository interface for DDD
"""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Optional, List
from .aggregate_root import AggregateRoot


T = TypeVar('T', bound=AggregateRoot)


class Repository(ABC, Generic[T]):
    """
    Base interface for all repositories
    
    A repository provides collection-like access to aggregates,
    hiding the details of data storage and retrieval.
    """
    
    @abstractmethod
    async def find_by_id(self, id: str) -> Optional[T]:
        """Find aggregate by ID"""
        pass
    
    @abstractmethod
    async def save(self, aggregate: T) -> None:
        """Save aggregate"""
        pass
    
    @abstractmethod
    async def delete(self, aggregate: T) -> None:
        """Delete aggregate"""
        pass
    
    @abstractmethod
    async def find_all(self) -> List[T]:
        """Find all aggregates"""
        pass
