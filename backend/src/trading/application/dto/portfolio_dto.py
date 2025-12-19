"""Portfolio DTO for data transfer"""
from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List


@dataclass(frozen=True)
class PositionDTO:
    """DTO for position data"""
    position_id: str
    symbol: str
    side: str
    quantity: Decimal
    entry_price: Decimal
    leverage: int
    unrealized_pnl: Decimal
    margin_used: Decimal
    liquidation_price: Decimal


@dataclass(frozen=True)
class BalanceDTO:
    """DTO for balance data"""
    asset: str
    free: Decimal
    locked: Decimal
    total: Decimal


@dataclass(frozen=True)
class PortfolioSnapshotDTO:
    """
    DTO for portfolio snapshot.
    
    Used to transfer portfolio data across layer boundaries.
    """
    account_id: str
    total_equity: Decimal
    available_balance: Decimal
    total_margin_used: Decimal
    unrealized_pnl: Decimal
    positions_count: int
    balances: List[BalanceDTO]
    positions: List[PositionDTO]
    
    @classmethod
    def from_aggregate(cls, portfolio) -> 'PortfolioSnapshotDTO':
        """
        Create DTO from PortfolioAggregate.
        
        Args:
            portfolio: PortfolioAggregate instance
        
        Returns:
            PortfolioSnapshotDTO
        """
        from src.trading.domain.portfolio.aggregates.portfolio_aggregate import PortfolioAggregate
        
        # Convert balances
        balances = [
            BalanceDTO(
                asset=balance.asset,
                free=balance.free,
                locked=balance.locked,
                total=balance.total
            )
            for balance in portfolio.balances.values()
        ]
        
        # Convert positions
        positions = [
            PositionDTO(
                position_id=position.id,
                symbol=position.symbol.to_exchange_format(),
                side=position.side,
                quantity=position.quantity,
                entry_price=position.entry_price,
                leverage=position.leverage,
                unrealized_pnl=position.unrealized_pnl,
                margin_used=position.margin_used,
                liquidation_price=position.calculate_liquidation_price()
            )
            for position in portfolio.positions.values()
        ]
        
        # Calculate totals
        total_equity = portfolio.calculate_total_equity()
        
        return cls(
            account_id=portfolio.account_id,
            total_equity=total_equity.amount,
            available_balance=portfolio.get_available_balance("USDT"),
            total_margin_used=portfolio.get_total_margin_used(),
            unrealized_pnl=portfolio.get_total_unrealized_pnl(),
            positions_count=len(portfolio.positions),
            balances=balances,
            positions=positions
        )
