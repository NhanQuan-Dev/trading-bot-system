"""Market data repository interfaces."""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime as dt
from uuid import UUID

from ..market_data import (
    MarketDataSubscription, 
    Candle, 
    Tick, 
    Trade, 
    OrderBook, 
    FundingRate,
    MarketStats,
    CandleInterval,
    DataType,
    StreamStatus
)


class IMarketDataSubscriptionRepository(ABC):
    """Repository interface for market data subscriptions."""
    
    @abstractmethod
    async def save(self, subscription: MarketDataSubscription) -> MarketDataSubscription:
        """Save or update subscription."""
        pass
    
    @abstractmethod
    async def find_by_id(self, subscription_id: UUID) -> Optional[MarketDataSubscription]:
        """Find subscription by ID."""
        pass
    
    @abstractmethod
    async def find_by_user(self, user_id: UUID) -> List[MarketDataSubscription]:
        """Find all subscriptions for a user."""
        pass
    
    @abstractmethod
    async def find_by_user_and_symbol(self, user_id: UUID, symbol: str) -> List[MarketDataSubscription]:
        """Find subscriptions by user and symbol."""
        pass
    
    @abstractmethod
    async def find_by_status(self, status: StreamStatus) -> List[MarketDataSubscription]:
        """Find subscriptions by status."""
        pass
    
    @abstractmethod
    async def find_active_subscriptions(self) -> List[MarketDataSubscription]:
        """Find all active subscriptions."""
        pass
    
    @abstractmethod
    async def delete(self, subscription_id: UUID) -> None:
        """Delete subscription."""
        pass


class ICandleRepository(ABC):
    """Repository interface for candle data."""
    
    @abstractmethod
    async def save(self, candle: Candle) -> None:
        """Save candle data."""
        pass
    
    @abstractmethod
    async def save_batch(self, candles: List[Candle]) -> None:
        """Save multiple candles."""
        pass
    
    @abstractmethod
    async def find_by_symbol_and_interval(
        self, 
        symbol: str, 
        interval: CandleInterval,
        start_time: Optional[dt] = None,
        end_time: Optional[dt] = None,
        limit: Optional[int] = None
    ) -> List[Candle]:
        """Find candles by symbol and interval within time range."""
        pass
    
    @abstractmethod
    async def find_latest(self, symbol: str, interval: CandleInterval) -> Optional[Candle]:
        """Find latest candle for symbol and interval."""
        pass
    
    @abstractmethod
    async def get_ohlc_data(
        self,
        symbol: str,
        interval: CandleInterval,
        start_time: dt,
        end_time: dt
    ) -> List[Dict[str, Any]]:
        """Get OHLC data formatted for charting."""
        pass


class ITickRepository(ABC):
    """Repository interface for tick data."""
    
    @abstractmethod
    async def save(self, tick: Tick) -> None:
        """Save tick data."""
        pass
    
    @abstractmethod
    async def save_batch(self, ticks: List[Tick]) -> None:
        """Save multiple ticks."""
        pass
    
    @abstractmethod
    async def find_by_symbol(
        self, 
        symbol: str,
        start_time: Optional[dt] = None,
        end_time: Optional[dt] = None,
        limit: Optional[int] = None
    ) -> List[Tick]:
        """Find ticks by symbol within time range."""
        pass
    
    @abstractmethod
    async def find_latest(self, symbol: str) -> Optional[Tick]:
        """Find latest tick for symbol."""
        pass
    
    @abstractmethod
    async def get_price_history(
        self,
        symbol: str,
        start_time: dt,
        end_time: dt
    ) -> List[Dict[str, Any]]:
        """Get price history data."""
        pass


class ITradeRepository(ABC):
    """Repository interface for trade data."""
    
    @abstractmethod
    async def save(self, trade: Trade) -> None:
        """Save trade data."""
        pass
    
    @abstractmethod
    async def save_batch(self, trades: List[Trade]) -> None:
        """Save multiple trades."""
        pass
    
    @abstractmethod
    async def find_by_symbol(
        self, 
        symbol: str,
        start_time: Optional[dt] = None,
        end_time: Optional[dt] = None,
        limit: Optional[int] = None
    ) -> List[Trade]:
        """Find trades by symbol within time range."""
        pass
    
    @abstractmethod
    async def find_latest(self, symbol: str) -> Optional[Trade]:
        """Find latest trade for symbol."""
        pass
    
    @abstractmethod
    async def get_volume_data(
        self,
        symbol: str,
        start_time: dt,
        end_time: dt
    ) -> List[Dict[str, Any]]:
        """Get volume analysis data."""
        pass


class IOrderBookRepository(ABC):
    """Repository interface for order book data."""
    
    @abstractmethod
    async def save(self, order_book: OrderBook) -> None:
        """Save order book snapshot."""
        pass
    
    @abstractmethod
    async def find_by_symbol(
        self, 
        symbol: str,
        start_time: Optional[dt] = None,
        end_time: Optional[dt] = None,
        limit: Optional[int] = None
    ) -> List[OrderBook]:
        """Find order book snapshots by symbol."""
        pass
    
    @abstractmethod
    async def find_latest(self, symbol: str) -> Optional[OrderBook]:
        """Find latest order book for symbol."""
        pass
    
    @abstractmethod
    async def get_depth_history(
        self,
        symbol: str,
        start_time: dt,
        end_time: dt
    ) -> List[Dict[str, Any]]:
        """Get order book depth history."""
        pass


class IMarketStatsRepository(ABC):
    """Repository interface for market statistics."""
    
    @abstractmethod
    async def save(self, stats: MarketStats) -> None:
        """Save market statistics."""
        pass
    
    @abstractmethod
    async def find_by_symbol(self, symbol: str) -> Optional[MarketStats]:
        """Find latest market stats for symbol."""
        pass
    
    @abstractmethod
    async def find_all_symbols(self) -> List[MarketStats]:
        """Find latest stats for all symbols."""
        pass
    
    @abstractmethod
    async def get_top_gainers(self, limit: int = 10) -> List[MarketStats]:
        """Get top price gainers."""
        pass
    
    @abstractmethod
    async def get_top_losers(self, limit: int = 10) -> List[MarketStats]:
        """Get top price losers."""
        pass
    
    @abstractmethod
    async def get_highest_volume(self, limit: int = 10) -> List[MarketStats]:
        """Get symbols with highest volume."""
        pass


__all__ = [
    "IMarketDataSubscriptionRepository",
    "ICandleRepository", 
    "ITickRepository",
    "ITradeRepository",
    "IOrderBookRepository",
    "IMarketStatsRepository",
]