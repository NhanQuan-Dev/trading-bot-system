"""Authentication use cases."""
from typing import Optional
import uuid
from datetime import datetime, timezone

from ...domain.user import User, Email, HashedPassword
from ...domain.user.repository import IUserRepository
from ...infrastructure.auth import create_token_pair, verify_refresh_token, TokenPair


class RegisterUserUseCase:
    """Use case for user registration."""
    
    def __init__(self, user_repository: IUserRepository):
        self._user_repository = user_repository
    
    async def execute(
        self,
        email: str,
        password: str,
        full_name: Optional[str] = None,
        timezone: str = "UTC",
    ) -> User:
        """
        Register a new user.
        
        Args:
            email: User email address
            password: Plain text password
            full_name: User's full name
            timezone: User timezone
        
        Returns:
            Created user entity
        
        Raises:
            ValueError: If email is already registered
        """
        # Check if email already exists
        if await self._user_repository.exists_by_email(email):
            raise ValueError(f"Email {email} is already registered")
        
        # Create user entity
        user = User.create(
            email=email,
            password=password,
            full_name=full_name,
            timezone=timezone,
        )
        
        # Save to database
        await self._user_repository.save(user)
        
        return user


class LoginUserUseCase:
    """Use case for user login."""
    
    def __init__(self, user_repository: IUserRepository):
        self._user_repository = user_repository
    
    async def execute(self, email: str, password: str) -> tuple[User, TokenPair]:
        """
        Login user and generate tokens.
        
        Args:
            email: User email address
            password: Plain text password
        
        Returns:
            Tuple of (User entity, TokenPair)
        
        Raises:
            ValueError: If credentials are invalid
        """
        # Find user by email
        user = await self._user_repository.find_by_email(email)
        
        if user is None:
            raise ValueError("Invalid email or password")
        
        # Verify password
        if not user.verify_password(password):
            raise ValueError("Invalid email or password")
        
        # Check if user is active
        if not user.is_active:
            raise ValueError("User account is inactive")
        
        # Update last login timestamp
        user.update_last_login()
        await self._user_repository.save(user)
        
        # Generate tokens
        token_pair = create_token_pair(user.id)
        
        return user, token_pair


class RefreshTokenUseCase:
    """Use case for refreshing access token."""
    
    def __init__(self, user_repository: IUserRepository):
        self._user_repository = user_repository
    
    async def execute(self, refresh_token: str) -> TokenPair:
        """
        Refresh access token using refresh token.
        
        Args:
            refresh_token: JWT refresh token
        
        Returns:
            New token pair
        
        Raises:
            ValueError: If refresh token is invalid or user not found
        """
        try:
            # Verify refresh token and extract user ID
            user_id = verify_refresh_token(refresh_token)
        except Exception as e:
            raise ValueError(f"Invalid refresh token: {str(e)}")
        
        # Find user
        user = await self._user_repository.find_by_id(user_id)
        
        if user is None:
            raise ValueError("User not found")
        
        if not user.is_active:
            raise ValueError("User account is inactive")
        
        # Generate new token pair
        token_pair = create_token_pair(user.id)
        
        return token_pair


class GetUserProfileUseCase:
    """Use case for getting user profile."""
    
    def __init__(self, user_repository: IUserRepository):
        self._user_repository = user_repository
    
    async def execute(self, user_id: uuid.UUID) -> Optional[User]:
        """
        Get user profile by ID.
        
        Args:
            user_id: User UUID
        
        Returns:
            User entity or None if not found
        """
        return await self._user_repository.find_by_id(user_id)


class UpdateUserProfileUseCase:
    """Use case for updating user profile."""
    
    def __init__(self, user_repository: IUserRepository):
        self._user_repository = user_repository
    
    async def execute(
        self,
        user_id: uuid.UUID,
        full_name: Optional[str] = None,
        timezone: Optional[str] = None,
        preferences: Optional[dict] = None,
    ) -> User:
        """
        Update user profile.
        
        Args:
            user_id: User UUID
            full_name: New full name
            timezone: New timezone
            preferences: New preferences
        
        Returns:
            Updated user entity
        
        Raises:
            ValueError: If user not found
        """
        user = await self._user_repository.find_by_id(user_id)
        
        if user is None:
            raise ValueError("User not found")
        
        # Update profile
        user.update_profile(
            full_name=full_name,
            timezone=timezone,
            preferences=preferences,
        )
        
        await self._user_repository.save(user)
        
        return user


class ChangePasswordUseCase:
    """Use case for changing user password."""
    
    def __init__(self, user_repository: IUserRepository):
        self._user_repository = user_repository
    
    async def execute(
        self,
        user_id: uuid.UUID,
        current_password: str,
        new_password: str,
    ) -> None:
        """
        Change user password.
        
        Args:
            user_id: User UUID
            current_password: Current password
            new_password: New password
        
        Raises:
            ValueError: If user not found or current password is incorrect
        """
        user = await self._user_repository.find_by_id(user_id)
        
        if user is None:
            raise ValueError("User not found")
        
        # Change password (will verify current password)
        user.change_password(current_password, new_password)
        
        await self._user_repository.save(user)
