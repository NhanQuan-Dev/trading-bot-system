"""Portfolio repository interface"""
from abc import ABC, abstractmethod
from typing import Optional
from ..aggregates.portfolio_aggregate import PortfolioAggregate


class PortfolioRepository(ABC):
    """
    Repository interface for PortfolioAggregate.
    
    This interface is defined in the domain layer.
    Implementations belong in the infrastructure layer.
    """
    
    @abstractmethod
    async def get_by_account(self, account_id: str) -> Optional[PortfolioAggregate]:
        """
        Get portfolio by account ID.
        
        Args:
            account_id: Account identifier
        
        Returns:
            PortfolioAggregate or None if not found
        """
        pass
    
    @abstractmethod
    async def save(self, portfolio: PortfolioAggregate) -> None:
        """
        Save portfolio aggregate.
        
        This method should:
        1. Persist the aggregate state
        2. Publish domain events
        3. Clear domain events from aggregate
        
        Args:
            portfolio: Portfolio aggregate to save
        """
        pass
    
    @abstractmethod
    async def delete(self, account_id: str) -> None:
        """
        Delete portfolio by account ID.
        
        Args:
            account_id: Account identifier
        """
        pass
