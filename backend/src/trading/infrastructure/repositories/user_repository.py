"""User repository implementation with SQLAlchemy."""
from typing import Optional
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...domain.user import User, Email, HashedPassword
from ...domain.user.repository import IUserRepository
from ..persistence.models.core_models import UserModel


class UserRepository(IUserRepository):
    """SQLAlchemy implementation of User repository."""
    
    def __init__(self, session: AsyncSession):
        self._session = session
    
    async def save(self, user: User) -> None:
        """
        Save or update user.
        
        Args:
            user: User entity to save
        """
        # Check if user exists
        stmt = select(UserModel).where(UserModel.id == user.id)
        result = await self._session.execute(stmt)
        existing = result.scalar_one_or_none()
        
        if existing:
            # Update existing user
            existing.email = user.email.value
            existing.password_hash = user.password.value
            existing.full_name = user.full_name
            existing.timezone = user.timezone
            existing.preferences = user.preferences
            existing.is_active = user.is_active
            existing.last_login = user.last_login_at
        else:
            # Create new user
            user_model = UserModel(
                id=user.id,
                email=user.email.value,
                password_hash=user.password.value,
                full_name=user.full_name,
                timezone=user.timezone,
                preferences=user.preferences,
                is_active=user.is_active,
                last_login=user.last_login_at,
            )
            self._session.add(user_model)
        
        await self._session.flush()
    
    async def find_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        """
        Find user by ID.
        
        Args:
            user_id: User UUID
        
        Returns:
            User entity or None if not found
        """
        stmt = select(UserModel).where(
            UserModel.id == user_id,
            UserModel.deleted_at.is_(None)
        )
        result = await self._session.execute(stmt)
        user_model = result.scalar_one_or_none()
        
        if user_model is None:
            return None
        
        return self._model_to_entity(user_model)
    
    async def find_by_email(self, email: str) -> Optional[User]:
        """
        Find user by email.
        
        Args:
            email: User email address
        
        Returns:
            User entity or None if not found
        """
        stmt = select(UserModel).where(
            UserModel.email == email,
            UserModel.deleted_at.is_(None)
        )
        result = await self._session.execute(stmt)
        user_model = result.scalar_one_or_none()
        
        if user_model is None:
            return None
        
        return self._model_to_entity(user_model)
    
    async def exists_by_email(self, email: str) -> bool:
        """
        Check if user exists by email.
        
        Args:
            email: User email address
        
        Returns:
            True if user exists, False otherwise
        """
        stmt = select(UserModel.id).where(
            UserModel.email == email.value,
            UserModel.deleted_at.is_(None)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None
    
    async def delete(self, user_id: uuid.UUID) -> None:
        """
        Soft delete user.
        
        Args:
            user_id: User UUID
        """
        stmt = select(UserModel).where(UserModel.id == user_id)
        result = await self._session.execute(stmt)
        user_model = result.scalar_one_or_none()
        
        if user_model:
            user_model.soft_delete()
            await self._session.flush()
    
    def _model_to_entity(self, model: UserModel) -> User:
        """
        Convert UserModel to User entity.
        
        Args:
            model: UserModel instance
        
        Returns:
            User entity
        """
        return User(
            id=model.id,
            email=Email(model.email),
            password=HashedPassword(value=model.password_hash),
            full_name=model.full_name,
            timezone=model.timezone,
            preferences=model.preferences or {},
            is_active=model.is_active,
            created_at=model.created_at,
            last_login_at=model.last_login,
        )
