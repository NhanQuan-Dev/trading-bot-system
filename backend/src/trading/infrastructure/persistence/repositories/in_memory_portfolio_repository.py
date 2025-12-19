"""In-memory portfolio repository implementation"""
from typing import Dict, Optional

from src.trading.domain.portfolio.repositories.portfolio_repository import PortfolioRepository
from src.trading.domain.portfolio.aggregates.portfolio_aggregate import PortfolioAggregate
from src.trading.shared.kernel.domain_event_bus import DomainEventBus


class InMemoryPortfolioRepository(PortfolioRepository):
    """
    In-memory implementation of PortfolioRepository.
    
    Used for:
    - Development and testing
    - Fast prototyping
    - Unit tests
    
    Note: Data is not persisted between restarts.
    """
    
    def __init__(self, event_bus: Optional[DomainEventBus] = None):
        self._storage: Dict[str, PortfolioAggregate] = {}
        self._event_bus = event_bus or DomainEventBus()
    
    async def get_by_account(self, account_id: str) -> Optional[PortfolioAggregate]:
        """Get portfolio by account ID"""
        return self._storage.get(account_id)
    
    async def save(self, portfolio: PortfolioAggregate) -> None:
        """Save portfolio and publish domain events"""
        # Store aggregate
        self._storage[portfolio.account_id] = portfolio
        
        # Publish domain events
        for event in portfolio.domain_events:
            await self._event_bus.publish(event)
        
        # Clear events after publishing
        portfolio.clear_domain_events()
    
    async def delete(self, account_id: str) -> None:
        """Delete portfolio"""
        if account_id in self._storage:
            del self._storage[account_id]
    
    # Additional methods for testing
    
    def clear(self) -> None:
        """Clear all portfolios (for testing)"""
        self._storage.clear()
    
    def count(self) -> int:
        """Get number of portfolios stored"""
        return len(self._storage)
