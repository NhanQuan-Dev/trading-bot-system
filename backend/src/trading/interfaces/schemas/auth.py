"""Authentication API schemas."""
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional
from datetime import datetime
import uuid


class UserRegisterRequest(BaseModel):
    """User registration request."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, max_length=100, description="Password (8-100 characters)")
    full_name: Optional[str] = Field(None, max_length=255, description="Full name")
    timezone: str = Field("UTC", description="User timezone")


class UserLoginRequest(BaseModel):
    """User login request."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class TokenResponse(BaseModel):
    """Token response."""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="Bearer", description="Token type")


class RefreshTokenRequest(BaseModel):
    """Refresh token request."""
    refresh_token: str = Field(..., description="JWT refresh token")


class UserResponse(BaseModel):
    """User response."""
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID = Field(..., description="User UUID")
    email: str = Field(..., description="User email address")
    full_name: Optional[str] = Field(None, description="Full name")
    timezone: str = Field(..., description="User timezone")
    is_active: bool = Field(..., description="Whether user is active")
    created_at: datetime = Field(..., description="Account creation timestamp")
    last_login_at: Optional[datetime] = Field(None, description="Last login timestamp")


class UserProfileUpdateRequest(BaseModel):
    """User profile update request."""
    full_name: Optional[str] = Field(None, max_length=255, description="Full name")
    timezone: Optional[str] = Field(None, description="User timezone")
    preferences: Optional[dict] = Field(None, description="User preferences")


class ChangePasswordRequest(BaseModel):
    """Change password request."""
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, max_length=100, description="New password (8-100 characters)")
