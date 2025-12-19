"""User domain - Value Objects and Entities."""
from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime
from datetime import timezone as dt_timezone
from passlib.context import CryptContext
import uuid
import re


# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@dataclass(frozen=True)
class Email:
    """Email value object with validation."""
    
    value: str
    
    EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    
    def __post_init__(self):
        """Validate email format."""
        if not self.EMAIL_REGEX.match(self.value):
            raise ValueError(f"Invalid email format: {self.value}")
    
    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class HashedPassword:
    """Hashed password value object."""
    
    value: str
    
    @classmethod
    def from_plain(cls, plain_password: str) -> "HashedPassword":
        """Create hashed password from plain text."""
        if len(plain_password) < 8:
            raise ValueError("Password must be at least 8 characters")
        if len(plain_password) > 100:
            raise ValueError("Password must be at most 100 characters")
        
        hashed = pwd_context.hash(plain_password)
        return cls(value=hashed)
    
    def verify(self, plain_password: str) -> bool:
        """Verify plain password against hashed password."""
        return pwd_context.verify(plain_password, self.value)


class User:
    """User aggregate root."""
    
    def __init__(
        self,
        id: uuid.UUID,
        email: Email,
        password: HashedPassword,
        full_name: Optional[str] = None,
        timezone: str = "UTC",
        is_active: bool = True,
        preferences: Optional[Dict[str, Any]] = None,
        created_at: Optional[datetime] = None,
        last_login_at: Optional[datetime] = None,
    ):
        self.id = id
        self.email = email
        self.password = password
        self.full_name = full_name
        self.timezone = timezone
        self.is_active = is_active
        self.preferences = preferences or {}
        
        self.created_at = created_at or datetime.now(dt_timezone.utc)
        self.last_login_at = last_login_at
        self.updated_at = datetime.now(dt_timezone.utc)
    
    @classmethod
    def create(
        cls,
        email: str,
        password: str,
        full_name: Optional[str] = None,
        timezone: str = "UTC",
    ) -> "User":
        """Create a new user."""
        return cls(
            id=uuid.uuid4(),
            email=Email(value=email),
            password=HashedPassword.from_plain(password),
            full_name=full_name,
            timezone=timezone,
            is_active=True,
        )
    
    def verify_password(self, plain_password: str) -> bool:
        """Verify user password."""
        if not self.is_active:
            raise ValueError("User account is not active")
        return self.password.verify(plain_password)
    
    def change_password(self, old_password: str, new_password: str) -> None:
        """Change user password."""
        if not self.verify_password(old_password):
            raise ValueError("Current password is incorrect")
        
        self.password = HashedPassword.from_plain(new_password)
        self.updated_at = datetime.now(dt_timezone.utc)
    
    def update_profile(
        self,
        full_name: Optional[str] = None,
        timezone: Optional[str] = None,
        preferences: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Update user profile."""
        if full_name is not None:
            self.full_name = full_name
        if timezone is not None:
            self.timezone = timezone
        if preferences is not None:
            self.preferences = preferences or {}
        
        self.updated_at = datetime.now(dt_timezone.utc)
    
    def update_preferences(self, preferences: Dict[str, Any]) -> None:
        """Update user preferences."""
        self.preferences = preferences or {}
        self.updated_at = datetime.now(dt_timezone.utc)
    
    def update_last_login(self) -> None:
        """Update last login timestamp."""
        self.last_login_at = datetime.now(dt_timezone.utc)
        self.updated_at = datetime.now(dt_timezone.utc)
    
    def activate(self) -> None:
        """Activate user account."""
        self.is_active = True
        self.updated_at = datetime.now(dt_timezone.utc)
    
    def deactivate(self) -> None:
        """Deactivate user account."""
        self.is_active = False
        self.updated_at = datetime.now(dt_timezone.utc)
    
    def __repr__(self) -> str:
        return f"User(id={self.id}, email={self.email.value}, is_active={self.is_active})"
