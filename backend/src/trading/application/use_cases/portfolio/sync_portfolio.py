"""Sync portfolio use case"""
from typing import Optional
from decimal import Decimal

from src.trading.domain.portfolio.aggregates.portfolio_aggregate import PortfolioAggregate
from src.trading.domain.portfolio.repositories.portfolio_repository import PortfolioRepository
from src.trading.application.dto.portfolio_dto import PortfolioSnapshotDTO
from src.trading.shared.errors.application_errors import ApplicationError


class SyncPortfolioUseCase:
    """
    Use case: Synchronize portfolio state from exchange.
    
    Responsibilities:
        1. Fetch account data from exchange
        2. Update portfolio aggregate with latest balances
        3. Persist changes
        4. Return portfolio snapshot
    """
    
    def __init__(
        self,
        portfolio_repository: PortfolioRepository,
        exchange_gateway: 'ExchangeGateway'  # Forward reference
    ):
        self._repository = portfolio_repository
        self._gateway = exchange_gateway
    
    async def execute(self, account_id: str) -> PortfolioSnapshotDTO:
        """
        Execute sync portfolio use case.
        
        Args:
            account_id: Account identifier
        
        Returns:
            PortfolioSnapshotDTO with current state
        
        Raises:
            ApplicationError: If sync fails
        """
        try:
            # 1. Fetch account data from exchange
            account_data = await self._gateway.get_account_info()
            
            # 2. Get or create portfolio aggregate
            portfolio = await self._repository.get_by_account(account_id)
            if portfolio is None:
                portfolio = PortfolioAggregate(account_id)
            
            # 3. Update balances from exchange
            for balance_data in account_data.balances:
                portfolio.update_balance(
                    asset=balance_data.asset,
                    free=balance_data.free,
                    locked=balance_data.locked
                )
            
            # 4. Update positions from exchange (if provided)
            if hasattr(account_data, 'positions'):
                for position_data in account_data.positions:
                    # Update existing position P&L
                    if portfolio.has_position(position_data.symbol):
                        portfolio.update_position_pnl(
                            position_data.symbol,
                            position_data.mark_price
                        )
            
            # 5. Persist changes
            await self._repository.save(portfolio)
            
            # 6. Return DTO
            return PortfolioSnapshotDTO.from_aggregate(portfolio)
            
        except Exception as e:
            raise ApplicationError(f"Failed to sync portfolio: {str(e)}") from e


class GetPortfolioSnapshotUseCase:
    """
    Use case: Get portfolio snapshot.
    
    Simple read operation without external sync.
    """
    
    def __init__(self, portfolio_repository: PortfolioRepository):
        self._repository = portfolio_repository
    
    async def execute(self, account_id: str) -> Optional[PortfolioSnapshotDTO]:
        """
        Get portfolio snapshot.
        
        Args:
            account_id: Account identifier
        
        Returns:
            PortfolioSnapshotDTO or None if portfolio not found
        """
        portfolio = await self._repository.get_by_account(account_id)
        
        if portfolio is None:
            return None
        
        return PortfolioSnapshotDTO.from_aggregate(portfolio)
