"""User API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any
import pytz

from .schemas.auth import UserResponse
from ....infrastructure.persistence.database import get_db
from ....infrastructure.repositories.user_repository import UserRepository
from ....interfaces.dependencies.auth import get_current_active_user
from ....domain.user import User


router = APIRouter(prefix="/users", tags=["Users"])


class UpdateProfileRequest(BaseModel):
    """Update user profile request."""
    
    full_name: Optional[str] = Field(None, max_length=255, description="User full name")
    timezone: Optional[str] = Field(None, description="User timezone")
    
    @validator('timezone')
    def validate_timezone(cls, v):
        if v is None:
            return v
        if v and v not in pytz.all_timezones:
            raise ValueError('Invalid timezone')
        return v
    
    @validator('full_name')
    def validate_full_name(cls, v):
        if v is not None and len(v.strip()) == 0:
            raise ValueError('Full name cannot be empty')
        return v


class UpdatePreferencesRequest(BaseModel):
    """Update user preferences request."""
    
    preferences: Dict[str, Any] = Field(..., description="User preferences")



import logging
logger = logging.getLogger(__name__)

# ...

@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_active_user),
):
    """
    Get current user profile.
    
    Args:
        current_user: Current authenticated user
    
    Returns:
        User profile information
    """
    return UserResponse(
        id=current_user.id,
        email=current_user.email.value,
        full_name=current_user.full_name,
        timezone=current_user.timezone,
        is_active=current_user.is_active,
        preferences=current_user.preferences,
        created_at=current_user.created_at,
        last_login_at=current_user.last_login_at,
    )


@router.patch("/me", response_model=UserResponse)
async def update_profile(
    request: UpdateProfileRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update current user profile.
    
    Args:
        request: Profile update data
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        Updated user profile
    """
    user_repo = UserRepository(db)
    
    # Update profile
    if request.full_name is not None or request.timezone is not None:
        current_user.update_profile(
            full_name=request.full_name,
            timezone=request.timezone,
        )
        
        await user_repo.save(current_user)
        await db.commit()
    
    return UserResponse(
        id=current_user.id,
        email=current_user.email.value,
        full_name=current_user.full_name,
        timezone=current_user.timezone,
        is_active=current_user.is_active,
        preferences=current_user.preferences,
        created_at=current_user.created_at,
        last_login_at=current_user.last_login_at,
    )


@router.put("/me/preferences", response_model=UserResponse)
async def update_preferences(
    preferences: Dict[str, Any],
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update user preferences.
    
    Args:
        preferences: User preferences dictionary
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        Updated user profile
    """
    user_repo = UserRepository(db)
    
    # Replace preferences entirely (empty payload should clear existing prefs)
    new_preferences = dict(preferences or {})
    current_user.update_preferences(new_preferences)
    
    await user_repo.save(current_user)
    await db.commit()
    
    return UserResponse(
        id=current_user.id,
        email=current_user.email.value,
        full_name=current_user.full_name,
        timezone=current_user.timezone,
        is_active=current_user.is_active,
        preferences=current_user.preferences,
        created_at=current_user.created_at,
        last_login_at=current_user.last_login_at,
    )
