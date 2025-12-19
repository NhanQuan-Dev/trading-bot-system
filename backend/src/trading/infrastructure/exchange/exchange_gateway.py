"""Exchange gateway interface and DTOs"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from typing import List, Optional


@dataclass
class BalanceData:
    """DTO for balance data from exchange"""
    asset: str
    free: Decimal
    locked: Decimal


@dataclass
class PositionData:
    """DTO for position data from exchange"""
    symbol: str
    side: str
    quantity: Decimal
    entry_price: Decimal
    mark_price: Decimal
    leverage: int
    unrealized_pnl: Decimal


@dataclass
class AccountInfoData:
    """DTO for account info from exchange"""
    account_id: str
    balances: List[BalanceData]
    positions: Optional[List[PositionData]] = None
    total_balance: Optional[Decimal] = None
    available_balance: Optional[Decimal] = None


class ExchangeGateway(ABC):
    """
    Domain interface for exchange operations.
    
    This interface is used by application use cases.
    Implementations (e.g., BinanceAdapter) are in infrastructure layer.
    """
    
    @abstractmethod
    async def get_account_info(self) -> AccountInfoData:
        """
        Get account balances and positions.
        
        Returns:
            AccountInfoData with balances and positions
        
        Raises:
            ExchangeAPIError: If API call fails
        """
        pass
    
    @abstractmethod
    async def get_balance(self, asset: str) -> BalanceData:
        """
        Get balance for specific asset.
        
        Args:
            asset: Asset symbol
        
        Returns:
            BalanceData
        """
        pass
    
    @abstractmethod
    async def test_connectivity(self) -> bool:
        """
        Test exchange connectivity.
        
        Returns:
            True if connected, False otherwise
        """
        pass
