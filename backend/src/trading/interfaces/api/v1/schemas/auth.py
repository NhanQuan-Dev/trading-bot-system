"""Authentication API schemas."""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Dict, Any
from datetime import datetime
import uuid


class RegisterRequest(BaseModel):
    """User registration request."""
    
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, max_length=100, description="User password")
    full_name: Optional[str] = Field(None, max_length=255, description="User full name")
    timezone: Optional[str] = Field("UTC", description="User timezone")


class LoginRequest(BaseModel):
    """User login request."""
    
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class RefreshTokenRequest(BaseModel):
    """Refresh token request."""
    
    refresh_token: str = Field(..., description="Refresh token")


class TokenResponse(BaseModel):
    """Token response."""
    
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="Bearer", description="Token type")


class UserResponse(BaseModel):
    """User information response."""
    
    id: uuid.UUID = Field(..., description="User UUID")
    email: str = Field(..., description="User email address")
    full_name: Optional[str] = Field(None, description="User full name")
    timezone: str = Field(..., description="User timezone")
    is_active: bool = Field(..., description="User active status")
    preferences: Optional[Dict[str, Any]] = Field(default_factory=dict, description="User preferences")
    created_at: datetime = Field(..., description="Account creation timestamp")
    last_login_at: Optional[datetime] = Field(None, description="Last login timestamp")
    
    class Config:
        """Pydantic config."""
        from_attributes = True
