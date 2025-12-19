"""Authentication API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...infrastructure.persistence.database import get_db
from ...infrastructure.repositories import UserRepository
from ...application.use_cases import (
    RegisterUserUseCase,
    LoginUserUseCase,
    RefreshTokenUseCase,
    GetUserProfileUseCase,
    UpdateUserProfileUseCase,
    ChangePasswordUseCase,
)
from ..schemas import (
    UserRegisterRequest,
    UserLoginRequest,
    TokenResponse,
    RefreshTokenRequest,
    UserResponse,
    UserProfileUpdateRequest,
    ChangePasswordRequest,
)
from ..dependencies import get_current_user
from ...domain.user import User


router = APIRouter(prefix="/auth", tags=["Authentication"])


def get_user_repository(db: AsyncSession = Depends(get_db)) -> UserRepository:
    """Dependency for user repository."""
    return UserRepository(db)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    request: UserRegisterRequest,
    user_repository: UserRepository = Depends(get_user_repository),
):
    """
    Register a new user.
    
    **Request Body:**
    - email: Valid email address (required)
    - password: Password with 8-100 characters (required)
    - full_name: User's full name (optional)
    - timezone: User timezone (default: UTC)
    
    **Returns:**
    - User profile with UUID, email, and account details
    
    **Errors:**
    - 400: Email already registered
    - 422: Validation error (invalid email, short password, etc.)
    """
    use_case = RegisterUserUseCase(user_repository)
    
    try:
        user = await use_case.execute(
            email=request.email,
            password=request.password,
            full_name=request.full_name,
            timezone=request.timezone,
        )
        
        return UserResponse(
            id=user.id,
            email=user.email.value,
            full_name=user.full_name,
            timezone=user.timezone,
            is_active=user.is_active,
            created_at=user.created_at,
            last_login_at=user.last_login_at,
        )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/login", response_model=TokenResponse)
async def login_user(
    request: UserLoginRequest,
    user_repository: UserRepository = Depends(get_user_repository),
):
    """
    Login user and receive JWT tokens.
    
    **Request Body:**
    - email: User email address (required)
    - password: User password (required)
    
    **Returns:**
    - access_token: JWT access token (valid for 30 minutes)
    - refresh_token: JWT refresh token (valid for 7 days)
    - token_type: Bearer
    
    **Errors:**
    - 401: Invalid credentials or inactive account
    """
    use_case = LoginUserUseCase(user_repository)
    
    try:
        user, token_pair = await use_case.execute(
            email=request.email,
            password=request.password,
        )
        
        return TokenResponse(
            access_token=token_pair.access_token,
            refresh_token=token_pair.refresh_token,
            token_type=token_pair.token_type,
        )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: RefreshTokenRequest,
    user_repository: UserRepository = Depends(get_user_repository),
):
    """
    Refresh access token using refresh token.
    
    **Request Body:**
    - refresh_token: Valid JWT refresh token (required)
    
    **Returns:**
    - New access_token and refresh_token pair
    
    **Errors:**
    - 401: Invalid or expired refresh token
    """
    use_case = RefreshTokenUseCase(user_repository)
    
    try:
        token_pair = await use_case.execute(request.refresh_token)
        
        return TokenResponse(
            access_token=token_pair.access_token,
            refresh_token=token_pair.refresh_token,
            token_type=token_pair.token_type,
        )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
):
    """
    Get current authenticated user profile.
    
    **Authentication:** Required (Bearer token)
    
    **Returns:**
    - User profile with UUID, email, and account details
    
    **Errors:**
    - 401: Invalid or missing token
    - 403: Inactive user account
    """
    return UserResponse(
        id=current_user.id,
        email=current_user.email.value,
        full_name=current_user.full_name,
        timezone=current_user.timezone,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        last_login_at=current_user.last_login_at,
    )


@router.patch("/me", response_model=UserResponse)
async def update_user_profile(
    request: UserProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    user_repository: UserRepository = Depends(get_user_repository),
):
    """
    Update current user profile.
    
    **Authentication:** Required (Bearer token)
    
    **Request Body:**
    - full_name: New full name (optional)
    - timezone: New timezone (optional)
    - preferences: User preferences dict (optional)
    
    **Returns:**
    - Updated user profile
    
    **Errors:**
    - 401: Invalid or missing token
    - 403: Inactive user account
    """
    use_case = UpdateUserProfileUseCase(user_repository)
    
    try:
        user = await use_case.execute(
            user_id=current_user.id,
            full_name=request.full_name,
            timezone=request.timezone,
            preferences=request.preferences,
        )
        
        return UserResponse(
            id=user.id,
            email=user.email.value,
            full_name=user.full_name,
            timezone=user.timezone,
            is_active=user.is_active,
            created_at=user.created_at,
            last_login_at=user.last_login_at,
        )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    user_repository: UserRepository = Depends(get_user_repository),
):
    """
    Change user password.
    
    **Authentication:** Required (Bearer token)
    
    **Request Body:**
    - current_password: Current password (required)
    - new_password: New password with 8-100 characters (required)
    
    **Returns:**
    - 204 No Content on success
    
    **Errors:**
    - 400: Invalid current password
    - 401: Invalid or missing token
    - 403: Inactive user account
    """
    use_case = ChangePasswordUseCase(user_repository)
    
    try:
        await use_case.execute(
            user_id=current_user.id,
            current_password=request.current_password,
            new_password=request.new_password,
        )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
