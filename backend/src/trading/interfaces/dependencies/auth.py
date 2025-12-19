"""FastAPI authentication dependencies."""
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from jose import JWTError
import uuid

from ...infrastructure.auth import verify_access_token
from ...infrastructure.persistence.database import get_db
from ...domain.user import User


# OAuth2 Bearer token scheme
security = HTTPBearer()


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> uuid.UUID:
    """
    Extract and verify user ID from JWT token.
    
    Args:
        credentials: HTTP authorization credentials
    
    Returns:
        User UUID
    
    Raises:
        HTTPException: If token is invalid
    """
    token = credentials.credentials
    
    try:
        user_id = verify_access_token(token)
        return user_id
    
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication credentials: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Get current authenticated user.
    
    Args:
        user_id: User UUID from token
        db: Database session
    
    Returns:
        User entity
    
    Raises:
        HTTPException: If user not found or inactive
    """
    from ...infrastructure.repositories.user_repository import UserRepository
    
    user_repo = UserRepository(db)
    user = await user_repo.find_by_id(user_id)
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Get current active user.
    
    Args:
        current_user: Current user from get_current_user
    
    Returns:
        User entity
    
    Raises:
        HTTPException: If user is inactive
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )
    
    return current_user


async def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """
    Get current user if authenticated, otherwise None.
    Useful for endpoints that work for both authenticated and anonymous users.
    
    Args:
        credentials: HTTP authorization credentials (optional)
        db: Database session
    
    Returns:
        User entity or None
    """
    if credentials is None:
        return None
    
    try:
        from ...infrastructure.repositories.user_repository import UserRepository
        
        user_id = verify_access_token(credentials.credentials)
        user_repo = UserRepository(db)
        user = await user_repo.find_by_id(user_id)
        return user if user and user.is_active else None
    
    except JWTError:
        return None
