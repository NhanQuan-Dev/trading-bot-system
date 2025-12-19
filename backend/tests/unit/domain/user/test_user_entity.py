"""Unit tests for User entity."""

import pytest
from datetime import datetime, UTC
from uuid import uuid4

from src.trading.domain.user import User, Email, HashedPassword


class TestUserEntity:
    """Test User entity."""
    
    def test_user_creation_with_valid_data(self):
        """Test creating user with valid data."""
        user_id = uuid4()
        email = Email("user@example.com")
        password = HashedPassword.from_plain("SecurePass123")
        
        user = User(
            id=user_id,
            email=email,
            password=password,
            full_name="John Doe",
            timezone="UTC",
            is_active=True,
            created_at=datetime.now(UTC),
        )
        
        assert user.id == user_id
        assert user.email == email
        assert user.password == password
        assert user.full_name == "John Doe"
        assert user.timezone == "UTC"
        assert user.is_active is True
        assert user.created_at is not None
    
    def test_user_creation_with_minimal_data(self):
        """Test creating user with minimal required data."""
        email = Email("user@example.com")
        password = HashedPassword.from_plain("SecurePass123")
        
        user = User(
            id=uuid4(),
            email=email,
            password=password,
            full_name=None,
            timezone="UTC",
            is_active=True,
            created_at=datetime.now(UTC),
        )
        
        assert user.email == email
        assert user.password == password
        assert user.full_name is None
    
    def test_user_creation_with_email_string(self):
        """Test creating user with email as string."""
        email_str = "user@example.com"
        password = HashedPassword.from_plain("SecurePass123")
        
        user = User(
            id=uuid4(),
            email=Email(email_str),
            password=password,
            full_name="John Doe",
            timezone="UTC",
            is_active=True,
            created_at=datetime.now(UTC),
        )
        
        assert user.email.value == email_str
    
    def test_authenticate_with_correct_password(self):
        """Test user authentication with correct password."""
        plain_password = "SecurePass123"
        password = HashedPassword.from_plain(plain_password)
        
        user = User(
            id=uuid4(),
            email=Email("user@example.com"),
            password=password,
            full_name="John Doe",
            timezone="UTC",
            is_active=True,
            created_at=datetime.now(UTC),
        )
        
        assert user.verify_password(plain_password) is True
    
    def test_authenticate_with_incorrect_password(self):
        """Test user authentication with incorrect password."""
        password = HashedPassword.from_plain("SecurePass123")
        
        user = User(
            id=uuid4(),
            email=Email("user@example.com"),
            password=password,
            full_name="John Doe",
            timezone="UTC",
            is_active=True,
            created_at=datetime.now(UTC),
        )
        
        # verify_password should return False for incorrect passwords
        assert user.verify_password("WrongPassword") is False
        # Can't test empty string as it might raise error before reaching verify
    
    def test_update_profile(self):
        """Test updating user profile."""
        user = User(
            id=uuid4(),
            email=Email("user@example.com"),
            password=HashedPassword.from_plain("SecurePass123"),
            full_name="John Doe",
            timezone="UTC",
            is_active=True,
            created_at=datetime.now(UTC),
        )
        
        # Update profile
        user.update_profile(
            full_name="Jane Smith",
            timezone="America/New_York"
        )
        
        assert user.full_name == "Jane Smith"
        assert user.timezone == "America/New_York"
    
    def test_update_profile_partial(self):
        """Test partial profile update."""
        user = User(
            id=uuid4(),
            email=Email("user@example.com"),
            password=HashedPassword.from_plain("SecurePass123"),
            full_name="John Doe",
            timezone="UTC",
            is_active=True,
            created_at=datetime.now(UTC),
        )
        
        original_timezone = user.timezone
        
        # Update only full_name
        user.update_profile(full_name="Jane Smith")
        
        assert user.full_name == "Jane Smith"
        assert user.timezone == original_timezone  # Unchanged
    
    def test_activate_user(self):
        """Test activating user account."""
        user = User(
            id=uuid4(),
            email=Email("user@example.com"),
            password=HashedPassword.from_plain("SecurePass123"),
            full_name="John Doe",
            timezone="UTC",
            is_active=False,
            created_at=datetime.now(UTC),
        )
        
        assert user.is_active is False
        
        user.activate()
        
        assert user.is_active is True
    
    def test_deactivate_user(self):
        """Test deactivating user account."""
        user = User(
            id=uuid4(),
            email=Email("user@example.com"),
            password=HashedPassword.from_plain("SecurePass123"),
            full_name="John Doe",
            timezone="UTC",
            is_active=True,
            created_at=datetime.now(UTC),
        )
        
        assert user.is_active is True
        
        user.deactivate()
        
        assert user.is_active is False
    
    def test_update_last_login(self):
        """Test updating last login timestamp."""
        user = User(
            id=uuid4(),
            email=Email("user@example.com"),
            password=HashedPassword.from_plain("SecurePass123"),
            full_name="John Doe",
            timezone="UTC",
            is_active=True,
            created_at=datetime.now(UTC),
            last_login_at=None,
        )
        
        assert user.last_login_at is None
        
        user.update_last_login()
        
        assert user.last_login_at is not None
        assert isinstance(user.last_login_at, datetime)
    
    def test_update_last_login_multiple_times(self):
        """Test updating last login multiple times."""
        user = User(
            id=uuid4(),
            email=Email("user@example.com"),
            password=HashedPassword.from_plain("SecurePass123"),
            full_name="John Doe",
            timezone="UTC",
            is_active=True,
            created_at=datetime.now(UTC),
        )
        
        user.update_last_login()
        first_login = user.last_login_at
        
        import time
        time.sleep(0.1)  # Small delay
        
        user.update_last_login()
        second_login = user.last_login_at
        
        assert second_login > first_login
    
    def test_change_password(self):
        """Test changing user password."""
        old_password = "OldPass123"
        new_password = "NewPass456"
        
        user = User(
            id=uuid4(),
            email=Email("user@example.com"),
            password=HashedPassword.from_plain(old_password),
            full_name="John Doe",
            timezone="UTC",
            is_active=True,
            created_at=datetime.now(UTC),
        )
        
        # Use the built-in change_password method
        user.change_password(old_password, new_password)
        
        # Verify new password works
        assert user.verify_password(new_password) is True
    
    def test_user_string_representation(self):
        """Test user string representation."""
        user = User(
            id=uuid4(),
            email=Email("user@example.com"),
            password=HashedPassword.from_plain("SecurePass123"),
            full_name="John Doe",
            timezone="UTC",
            is_active=True,
            created_at=datetime.now(UTC),
        )
        
        user_str = str(user)
        assert "user@example.com" in user_str or "John Doe" in user_str
    
    def test_user_preferences(self):
        """Test user preferences management."""
        user = User(
            id=uuid4(),
            email=Email("user@example.com"),
            password=HashedPassword.from_plain("SecurePass123"),
            full_name="John Doe",
            timezone="UTC",
            is_active=True,
            created_at=datetime.now(UTC),
            preferences={"theme": "dark", "language": "en"}
        )
        
        assert user.preferences == {"theme": "dark", "language": "en"}
        
        # Update preferences
        user.preferences = {"theme": "light", "language": "vi"}
        assert user.preferences["theme"] == "light"
