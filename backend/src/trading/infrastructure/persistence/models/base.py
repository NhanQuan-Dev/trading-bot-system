"""Base model mixins and utilities."""
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import Column, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
import uuid


class TimestampMixin:
    """Mixin for created_at and updated_at timestamps."""
    
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Record creation timestamp (UTC)"
    )
    
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="Record last update timestamp (UTC)"
    )


class SoftDeleteMixin:
    """Mixin for soft delete functionality."""
    
    deleted_at = Column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        index=True,
        comment="Soft delete timestamp (NULL = active)"
    )
    
    def soft_delete(self) -> None:
        """Mark record as deleted."""
        self.deleted_at = datetime.now(timezone.utc)
    
    def restore(self) -> None:
        """Restore soft-deleted record."""
        self.deleted_at = None
    
    @property
    def is_deleted(self) -> bool:
        """Check if record is soft-deleted."""
        return self.deleted_at is not None
    
    @property
    def is_active(self) -> bool:
        """Check if record is active (not deleted)."""
        return self.deleted_at is None


class UUIDPrimaryKeyMixin:
    """Mixin for UUID v7 primary key."""
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,  # Note: Use uuid7() in production
        comment="UUID v7 primary key"
    )


def generate_uuid7() -> uuid.UUID:
    """
    Generate UUID v7 (time-ordered UUID).
    
    Note: This is a placeholder. In production, use a proper UUID v7 library
    like uuid6 package: `from uuid6 import uuid7`
    """
    # For now, use uuid4. Replace with uuid7() in production
    return uuid.uuid4()
