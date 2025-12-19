"""Market data use cases."""
from typing import List, Optional, Dict, Any
from datetime import datetime as dt
from uuid import UUID

from ...shared.exceptions import (
    NotFoundError, 
    ValidationError, 
    DuplicateError,
    BusinessException
)
from ...domain.market_data import (
    MarketDataSubscription,
    Candle,
    Tick,
    Trade,
    OrderBook,
    MarketStats,
    DataType,
    CandleInterval,
    StreamStatus
)
from ...domain.market_data.repository import (
    IMarketDataSubscriptionRepository,
    ICandleRepository,
    ITickRepository,
    ITradeRepository,
    IOrderBookRepository,
    IMarketStatsRepository
)


class CreateMarketDataSubscriptionUseCase:
    """Use case for creating market data subscriptions."""
    
    def __init__(self, subscription_repository: IMarketDataSubscriptionRepository):
        self.subscription_repository = subscription_repository
    
    async def execute(
        self,
        user_id: UUID,
        symbol: str,
        data_types: List[DataType],
        intervals: List[CandleInterval],
        exchange: str = "BINANCE",
    ) -> MarketDataSubscription:
        """Create a new market data subscription."""
        
        # Validate inputs
        if not data_types:
            raise ValidationError("At least one data type must be specified")
        
        if DataType.CANDLE in data_types and not intervals:
            raise ValidationError("Intervals must be specified for candle data")
        
        # Check if user already has subscription for this symbol
        existing_subscriptions = await self.subscription_repository.find_by_user_and_symbol(
            user_id, symbol
        )
        active_subscriptions = [s for s in existing_subscriptions if s.is_active()]
        
        if active_subscriptions:
            raise DuplicateError(f"Active subscription already exists for {symbol}")
        
        # Create subscription
        subscription = MarketDataSubscription.create(
            user_id=user_id,
            symbol=symbol,
            data_types=data_types,
            intervals=intervals,
            exchange=exchange,
        )
        
        # Save subscription
        saved_subscription = await self.subscription_repository.save(subscription)
        return saved_subscription


class GetMarketDataSubscriptionsUseCase:
    """Use case for retrieving user's market data subscriptions."""
    
    def __init__(self, subscription_repository: IMarketDataSubscriptionRepository):
        self.subscription_repository = subscription_repository
    
    async def execute(self, user_id: UUID) -> List[MarketDataSubscription]:
        """Get user's market data subscriptions."""
        return await self.subscription_repository.find_by_user(user_id)


class GetMarketDataSubscriptionUseCase:
    """Use case for retrieving a specific subscription."""
    
    def __init__(self, subscription_repository: IMarketDataSubscriptionRepository):
        self.subscription_repository = subscription_repository
    
    async def execute(self, user_id: UUID, subscription_id: UUID) -> MarketDataSubscription:
        """Get a specific market data subscription."""
        
        subscription = await self.subscription_repository.find_by_id(subscription_id)
        if not subscription:
            raise NotFoundError(f"Subscription with id {subscription_id} not found")
        
        # Verify ownership
        if subscription.user_id != user_id:
            raise ValidationError("Subscription does not belong to user")
        
        return subscription


class UpdateSubscriptionStatusUseCase:
    """Use case for updating subscription status."""
    
    def __init__(self, subscription_repository: IMarketDataSubscriptionRepository):
        self.subscription_repository = subscription_repository
    
    async def execute(
        self,
        subscription_id: UUID,
        status: StreamStatus,
        stream_url: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> MarketDataSubscription:
        """Update subscription status."""
        
        subscription = await self.subscription_repository.find_by_id(subscription_id)
        if not subscription:
            raise NotFoundError(f"Subscription with id {subscription_id} not found")
        
        # Update status based on type
        if status == StreamStatus.CONNECTED:
            subscription.mark_connected(stream_url or "")
        elif status == StreamStatus.DISCONNECTED:
            subscription.mark_disconnected(error_message)
        elif status == StreamStatus.ERROR:
            subscription.mark_error(error_message or "Unknown error")
        elif status == StreamStatus.RECONNECTING:
            subscription.mark_reconnecting()
        
        # Save updated subscription
        updated_subscription = await self.subscription_repository.save(subscription)
        return updated_subscription


class DeleteMarketDataSubscriptionUseCase:
    """Use case for deleting a subscription."""
    
    def __init__(self, subscription_repository: IMarketDataSubscriptionRepository):
        self.subscription_repository = subscription_repository
    
    async def execute(self, user_id: UUID, subscription_id: UUID) -> None:
        """Delete a market data subscription."""
        
        subscription = await self.subscription_repository.find_by_id(subscription_id)
        if not subscription:
            raise NotFoundError(f"Subscription with id {subscription_id} not found")
        
        # Verify ownership
        if subscription.user_id != user_id:
            raise ValidationError("Subscription does not belong to user")
        
        # Delete subscription
        await self.subscription_repository.delete(subscription_id)


class GetCandleDataUseCase:
    """Use case for retrieving candle data."""
    
    def __init__(self, candle_repository: ICandleRepository):
        self.candle_repository = candle_repository
    
    async def execute(
        self,
        symbol: str,
        interval: CandleInterval,
        start_time: Optional[dt] = None,
        end_time: Optional[dt] = None,
        limit: Optional[int] = None,
    ) -> List[Candle]:
        """Get candle data for symbol and interval."""
        
        return await self.candle_repository.find_by_symbol_and_interval(
            symbol=symbol,
            interval=interval,
            start_time=start_time,
            end_time=end_time,
            limit=limit
        )


class GetOHLCDataUseCase:
    """Use case for retrieving OHLC data formatted for charting."""
    
    def __init__(self, candle_repository: ICandleRepository):
        self.candle_repository = candle_repository
    
    async def execute(
        self,
        symbol: str,
        interval: CandleInterval,
        start_time: dt,
        end_time: dt,
    ) -> List[Dict[str, Any]]:
        """Get OHLC data for charting."""
        
        return await self.candle_repository.get_ohlc_data(
            symbol=symbol,
            interval=interval,
            start_time=start_time,
            end_time=end_time
        )


class GetTickDataUseCase:
    """Use case for retrieving tick data."""
    
    def __init__(self, tick_repository: ITickRepository):
        self.tick_repository = tick_repository
    
    async def execute(
        self,
        symbol: str,
        start_time: Optional[dt] = None,
        end_time: Optional[dt] = None,
        limit: Optional[int] = None,
    ) -> List[Tick]:
        """Get tick data for symbol."""
        
        return await self.tick_repository.find_by_symbol(
            symbol=symbol,
            start_time=start_time,
            end_time=end_time,
            limit=limit
        )


class GetLatestPriceUseCase:
    """Use case for getting latest price data."""
    
    def __init__(
        self, 
        tick_repository: ITickRepository,
        candle_repository: ICandleRepository
    ):
        self.tick_repository = tick_repository
        self.candle_repository = candle_repository
    
    async def execute(self, symbol: str) -> Dict[str, Any]:
        """Get latest price information for symbol."""
        
        # Get latest tick
        latest_tick = await self.tick_repository.find_latest(symbol)
        
        # Get latest 1m candle
        latest_candle = await self.candle_repository.find_latest(symbol, CandleInterval.ONE_MINUTE)
        
        result = {
            "symbol": symbol,
            "latest_price": None,
            "latest_timestamp": None,
            "candle_data": None,
        }
        
        if latest_tick:
            result["latest_price"] = float(latest_tick.price)
            result["latest_timestamp"] = latest_tick.timestamp.isoformat()
        
        if latest_candle:
            result["candle_data"] = {
                "open": float(latest_candle.open_price),
                "high": float(latest_candle.high_price),
                "low": float(latest_candle.low_price),
                "close": float(latest_candle.close_price),
                "volume": float(latest_candle.volume),
                "change": float(latest_candle.price_change),
                "change_percent": float(latest_candle.price_change_percent),
            }
        
        return result


class GetTradeDataUseCase:
    """Use case for retrieving trade data."""
    
    def __init__(self, trade_repository: ITradeRepository):
        self.trade_repository = trade_repository
    
    async def execute(
        self,
        symbol: str,
        start_time: Optional[dt] = None,
        end_time: Optional[dt] = None,
        limit: Optional[int] = None,
    ) -> List[Trade]:
        """Get trade data for symbol."""
        
        return await self.trade_repository.find_by_symbol(
            symbol=symbol,
            start_time=start_time,
            end_time=end_time,
            limit=limit
        )


class GetOrderBookUseCase:
    """Use case for retrieving order book data."""
    
    def __init__(self, orderbook_repository: IOrderBookRepository):
        self.orderbook_repository = orderbook_repository
    
    async def execute(self, symbol: str) -> Optional[OrderBook]:
        """Get latest order book for symbol."""
        
        return await self.orderbook_repository.find_latest(symbol)


class GetMarketStatsUseCase:
    """Use case for retrieving market statistics."""
    
    def __init__(self, stats_repository: IMarketStatsRepository):
        self.stats_repository = stats_repository
    
    async def execute(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Get market statistics."""
        
        if symbol:
            # Get stats for specific symbol
            stats = await self.stats_repository.find_by_symbol(symbol)
            return {"symbol": symbol, "stats": stats} if stats else {"symbol": symbol, "stats": None}
        else:
            # Get stats for all symbols
            all_stats = await self.stats_repository.find_all_symbols()
            return {"all_symbols": all_stats}


class GetMarketOverviewUseCase:
    """Use case for getting market overview with top gainers, losers, etc."""
    
    def __init__(self, stats_repository: IMarketStatsRepository):
        self.stats_repository = stats_repository
    
    async def execute(self, limit: int = 10) -> Dict[str, Any]:
        """Get market overview with top movers."""
        
        # Get top gainers, losers, and highest volume
        top_gainers = await self.stats_repository.get_top_gainers(limit)
        top_losers = await self.stats_repository.get_top_losers(limit)
        highest_volume = await self.stats_repository.get_highest_volume(limit)
        
        return {
            "top_gainers": top_gainers,
            "top_losers": top_losers,
            "highest_volume": highest_volume,
            "timestamp": dt.now().isoformat(),
        }


class StoreCandleDataUseCase:
    """Use case for storing candle data from external sources."""
    
    def __init__(self, candle_repository: ICandleRepository):
        self.candle_repository = candle_repository
    
    async def execute(self, candles: List[Candle]) -> None:
        """Store candle data."""
        
        if not candles:
            raise ValidationError("No candles provided")
        
        await self.candle_repository.save_batch(candles)


class StoreTickDataUseCase:
    """Use case for storing tick data from external sources."""
    
    def __init__(self, tick_repository: ITickRepository):
        self.tick_repository = tick_repository
    
    async def execute(self, ticks: List[Tick]) -> None:
        """Store tick data."""
        
        if not ticks:
            raise ValidationError("No ticks provided")
        
        await self.tick_repository.save_batch(ticks)