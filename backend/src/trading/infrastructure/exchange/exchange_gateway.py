"""Exchange gateway interface and DTOs"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from typing import List, Optional, Dict, Any


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
    @abstractmethod
    async def create_order(
        self,
        symbol: str,
        side: str,
        type: str,
        quantity: Decimal,
        price: Optional[Decimal] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create a new order.
        
        Args:
            symbol: Trading symbol
            side: 'BUY' or 'SELL'
            type: 'MARKET', 'LIMIT', etc.
            quantity: Order quantity
            price: Order price
            **kwargs: Additional parameters
            
        Returns:
            Order response dict
        """
        pass

    @abstractmethod
    async def cancel_order(self, symbol: str, order_id: str) -> Dict[str, Any]:
        """
        Cancel an order.
        
        Args:
            symbol: Trading symbol
            order_id: Order ID
            
        Returns:
            Cancel response dict
        """
        pass

    @abstractmethod
    async def get_order(self, symbol: str, order_id: str) -> Dict[str, Any]:
        """
        Get order details.
        
        Args:
            symbol: Trading symbol
            order_id: Order ID
            
        Returns:
            Order details dict
        """
        pass
        
    @abstractmethod
    async def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all open orders.
        
        Args:
            symbol: Optional trading symbol filter
            
        Returns:
            List of open orders
        """
        pass

    @abstractmethod
    async def get_ticker_price(self, symbol: str) -> Decimal:
        """
        Get current price for a symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Current price as Decimal
        """
        pass
