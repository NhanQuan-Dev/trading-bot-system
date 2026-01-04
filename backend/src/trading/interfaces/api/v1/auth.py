"""Authentication API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from jose import JWTError
from datetime import datetime, timezone

from .schemas.auth import (
    RegisterRequest,
    LoginRequest,
    RefreshTokenRequest,
    TokenResponse,
    UserResponse,
)
from ....infrastructure.persistence.database import get_db
from ....infrastructure.repositories.user_repository import UserRepository
from ....infrastructure.auth import create_token_pair, verify_refresh_token
from ....domain.user import User, Email, HashedPassword


router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Register a new user.
    
    Args:
        request: Registration data
        db: Database session
    
    Returns:
        JWT token pair
    
    Raises:
        HTTPException: If email already exists
    """
    user_repo = UserRepository(db)
    
    # Check if email exists
    email = Email(request.email)
    if await user_repo.exists_by_email(email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    
    # Create new user
    user = User.create(
        email=request.email,
        password=request.password,
        full_name=request.full_name,
        timezone=request.timezone or "UTC",
    )
    
    # Save user
    await user_repo.save(user)
    await db.commit()
    
    # Generate tokens
    token_pair = create_token_pair(user.id)
    
    return TokenResponse(
        access_token=token_pair.access_token,
        refresh_token=token_pair.refresh_token,
        token_type=token_pair.token_type,
    )



import logging
logger = logging.getLogger(__name__)

# ...

@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Login user and return JWT tokens.
    
    Args:
        request: Login credentials
        db: Database session
    
    Returns:
        JWT token pair
    
    Raises:
        HTTPException: If credentials are invalid
    """
    user_repo = UserRepository(db)
    
    # Find user by email
    user = await user_repo.find_by_email(request.email)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify password
    try:
        if not user.verify_password(request.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except ValueError:
        # Treat inactive account as unauthorized to avoid leaking status
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Update last login
    user.update_last_login()
    await user_repo.save(user)
    await db.commit()
    
    # Generate tokens
    token_pair = create_token_pair(user.id)
    
    return TokenResponse(
        access_token=token_pair.access_token,
        refresh_token=token_pair.refresh_token,
        token_type=token_pair.token_type,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Refresh access token using refresh token.
    
    Args:
        request: Refresh token
        db: Database session
    
    Returns:
        New JWT token pair
    
    Raises:
        HTTPException: If refresh token is invalid
    """
    try:
        user_id = verify_refresh_token(request.refresh_token)
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid refresh token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify user exists and is active
    user_repo = UserRepository(db)
    user = await user_repo.find_by_id(user_id)
    
    if not user:
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
    
    # Generate new tokens
    token_pair = create_token_pair(user.id)
    
    return TokenResponse(
        access_token=token_pair.access_token,
        refresh_token=token_pair.refresh_token,
        token_type=token_pair.token_type,
    )
