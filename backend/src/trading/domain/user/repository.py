"""User Repository Interface."""
from abc import ABC, abstractmethod
from typing import Optional
import uuid

from . import User


class IUserRepository(ABC):
    """User repository interface."""
    
    @abstractmethod
    async def save(self, user: User) -> None:
        """Save user."""
        pass
    
    @abstractmethod
    async def find_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        """Find user by ID."""
        pass
    
    @abstractmethod
    async def find_by_email(self, email: str) -> Optional[User]:
        """Find user by email."""
        pass
    
    @abstractmethod
    async def exists_by_email(self, email: str) -> bool:
        """Check if user exists by email."""
        pass
    
    @abstractmethod
    async def delete(self, user_id: uuid.UUID) -> None:
        """Delete user (soft delete)."""
        pass
