"""Risk repository interfaces module."""

from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from ..entities import RiskLimit, RiskAlert
from ..enums import RiskLimitType


class IRiskLimitRepository(ABC):
    """Repository interface for RiskLimit entities."""
    
    @abstractmethod
    async def save(self, risk_limit: RiskLimit) -> RiskLimit:
        """Save a risk limit."""
        pass
    
    @abstractmethod
    async def find_by_id(self, limit_id: UUID) -> Optional[RiskLimit]:
        """Find risk limit by ID."""
        pass
    
    @abstractmethod
    async def find_by_user(self, user_id: UUID) -> List[RiskLimit]:
        """Find all risk limits for a user."""
        pass
    
    @abstractmethod
    async def find_by_user_and_type(self, user_id: UUID, limit_type: RiskLimitType) -> List[RiskLimit]:
        """Find risk limits by user and type."""
        pass
    
    @abstractmethod
    async def find_by_user_and_symbol(self, user_id: UUID, symbol: str) -> List[RiskLimit]:
        """Find risk limits by user and symbol."""
        pass
    
    @abstractmethod
    async def find_enabled_by_user(self, user_id: UUID) -> List[RiskLimit]:
        """Find all enabled risk limits for a user."""
        pass
    
    @abstractmethod
    async def update(self, risk_limit: RiskLimit) -> RiskLimit:
        """Update a risk limit."""
        pass
    
    @abstractmethod
    async def delete(self, limit_id: UUID) -> bool:
        """Delete a risk limit."""
        pass


class IRiskAlertRepository(ABC):
    """Repository interface for RiskAlert entities."""
    
    @abstractmethod
    async def save(self, alert: RiskAlert) -> RiskAlert:
        """Save a risk alert."""
        pass
    
    @abstractmethod
    async def find_by_id(self, alert_id: UUID) -> Optional[RiskAlert]:
        """Find risk alert by ID."""
        pass
    
    @abstractmethod
    async def find_by_user(self, user_id: UUID) -> List[RiskAlert]:
        """Find all risk alerts for a user."""
        pass
    
    @abstractmethod
    async def find_unacknowledged_by_user(self, user_id: UUID) -> List[RiskAlert]:
        """Find unacknowledged risk alerts for a user."""
        pass
    
    @abstractmethod
    async def find_by_risk_limit(self, risk_limit_id: UUID) -> List[RiskAlert]:
        """Find alerts for a specific risk limit."""
        pass
    
    @abstractmethod
    async def update(self, alert: RiskAlert) -> RiskAlert:
        """Update a risk alert."""
        pass
    
    @abstractmethod
    async def delete(self, alert_id: UUID) -> bool:
        """Delete a risk alert."""
        pass
