"""SQLAlchemy implementations of market data repositories."""
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional, Dict, Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, or_, desc
from sqlalchemy.orm import selectinload

from ....domain.market_data import (
    MarketDataSubscription, Candle, Tick, Trade, OrderBook, MarketStats
)
from ....domain.market_data.repository import (
    IMarketDataSubscriptionRepository,
    ICandleRepository,
    ITickRepository,
    ITradeRepository,
    IOrderBookRepository,
    IMarketStatsRepository
)
from ....domain.market_data import (
    DataType, CandleInterval
)
from ..models.market_data_models import (
    MarketDataSubscriptionModel,
    MarketPriceModel,
    OrderBookSnapshotModel
)
from ..models.base import TimestampMixin
from ..database import AsyncSession as DatabaseSession


class MarketDataSubscriptionRepository(IMarketDataSubscriptionRepository):
    """SQLAlchemy implementation of market data subscription repository."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def save(self, subscription: MarketDataSubscription) -> MarketDataSubscription:
        """Save or update a market data subscription."""
        try:
            # Check if subscription exists
            stmt = select(MarketDataSubscriptionModel).where(
                MarketDataSubscriptionModel.id == subscription.id
            )
            result = await self._session.execute(stmt)
            model = result.scalar_one_or_none()

            if model is None:
                # Create new subscription
                model = self._domain_to_model(subscription)
                self._session.add(model)
            else:
                # Update existing subscription
                self._update_model_from_domain(model, subscription)

            await self._session.flush()
            await self._session.refresh(model)
            
            return self._model_to_domain(model)
        except Exception as e:
            await self._session.rollback()
            raise e

    async def find_by_id(self, subscription_id: UUID) -> Optional[MarketDataSubscription]:
        """Find subscription by ID."""
        stmt = select(MarketDataSubscriptionModel).where(
            MarketDataSubscriptionModel.id == subscription_id
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        
        return self._model_to_domain(model) if model else None

    async def find_by_user(self, user_id: UUID) -> List[MarketDataSubscription]:
        """Find all subscriptions for a user."""
        stmt = select(MarketDataSubscriptionModel).where(
            MarketDataSubscriptionModel.user_id == user_id
        ).order_by(MarketDataSubscriptionModel.created_at.desc())
        
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        
        return [self._model_to_domain(model) for model in models]

    async def find_by_symbol(self, symbol: str) -> List[MarketDataSubscription]:
        """Find all subscriptions for a symbol."""
        stmt = select(MarketDataSubscriptionModel).where(
            MarketDataSubscriptionModel.symbol == symbol
        ).order_by(MarketDataSubscriptionModel.created_at.desc())
        
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        
        return [self._model_to_domain(model) for model in models]

    async def find_active(self) -> List[MarketDataSubscription]:
        """Find all active subscriptions."""
        stmt = select(MarketDataSubscriptionModel).where(
            MarketDataSubscriptionModel.status.in_(["CONNECTED", "CONNECTING", "RECONNECTING"])
        ).order_by(MarketDataSubscriptionModel.created_at.desc())
        
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        
        return [self._model_to_domain(model) for model in models]

    async def delete(self, subscription_id: UUID) -> bool:
        """Delete a subscription."""
        stmt = select(MarketDataSubscriptionModel).where(
            MarketDataSubscriptionModel.id == subscription_id
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        
        if model:
            await self._session.delete(model)
            await self._session.flush()
            return True
        return False

    def _domain_to_model(self, subscription: MarketDataSubscription) -> MarketDataSubscriptionModel:
        """Convert domain entity to database model."""
        return MarketDataSubscriptionModel(
            id=subscription.id,
            user_id=subscription.user_id,
            symbol=subscription.symbol,
            data_types=[dt.value for dt in subscription.data_types],
            intervals=[interval.value for interval in subscription.intervals],
            status=subscription.status,
            exchange=subscription.exchange,
            stream_url=subscription.stream_url,
            last_message_at=subscription.last_message_at,
            error_message=subscription.error_message,
            reconnect_count=subscription.reconnect_count,
            meta_data=subscription.metadata or {},
            created_at=subscription.created_at,
            updated_at=subscription.updated_at
        )

    def _update_model_from_domain(self, model: MarketDataSubscriptionModel, subscription: MarketDataSubscription):
        """Update database model from domain entity."""
        model.symbol = subscription.symbol
        model.data_types = [dt.value for dt in subscription.data_types]
        model.intervals = [interval.value for interval in subscription.intervals]
        model.status = subscription.status
        model.exchange = subscription.exchange
        model.stream_url = subscription.stream_url
        model.last_message_at = subscription.last_message_at
        model.error_message = subscription.error_message
        model.reconnect_count = subscription.reconnect_count
        model.meta_data = subscription.metadata or {}
        model.updated_at = subscription.updated_at

    def _model_to_domain(self, model: MarketDataSubscriptionModel) -> MarketDataSubscription:
        """Convert database model to domain entity."""        
        return MarketDataSubscription(
            id=model.id,
            user_id=model.user_id,
            symbol=Symbol(model.symbol),
            data_types=[DataType(dt) for dt in model.data_types],
            intervals=[CandleInterval(interval) for interval in model.intervals],
            status=model.status,  # String value for now
            exchange=model.exchange,  # Use string directly
            stream_url=model.stream_url,
            last_message_at=model.last_message_at,
            error_message=model.error_message,
            reconnect_count=model.reconnect_count,
            metadata=model.meta_data or {},
            created_at=model.created_at or datetime.now(timezone.utc),
            updated_at=model.updated_at or datetime.now(timezone.utc)
        )


class CandleRepository(ICandleRepository):
    """SQLAlchemy implementation of candle repository."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def save(self, candle: Candle) -> Candle:
        """Save or update a candle."""
        try:
            # Check if candle exists (based on symbol, interval, and timestamp)
            stmt = select(MarketPriceModel).where(
                and_(
                    MarketPriceModel.symbol == candle.symbol,
                    MarketPriceModel.interval == candle.interval.value,
                    MarketPriceModel.timestamp == candle.open_time
                )
            )
            result = await self._session.execute(stmt)
            model = result.scalar_one_or_none()

            if model is None:
                # Create new candle
                model = self._domain_to_model(candle)
                self._session.add(model)
            else:
                # Update existing candle
                self._update_model_from_domain(model, candle)

            await self._session.flush()
            await self._session.refresh(model)
            
            return self._model_to_domain(model)
        except Exception as e:
            await self._session.rollback()
            raise e

    async def find_by_symbol_and_interval(
        self,
        symbol: str,
        interval: CandleInterval,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[Candle]:
        """Find candles by symbol and interval within time range."""
        stmt = select(MarketPriceModel).where(
            and_(
                MarketPriceModel.symbol == symbol,
                MarketPriceModel.interval == interval.value
            )
        )
        
        if start_time:
            stmt = stmt.where(MarketPriceModel.timestamp >= start_time)
        if end_time:
            stmt = stmt.where(MarketPriceModel.timestamp <= end_time)
            
        stmt = stmt.order_by(MarketPriceModel.timestamp.desc()).limit(limit)
        
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        
        return [self._model_to_domain(model) for model in models]

    async def find_latest(self, symbol: str, interval: CandleInterval) -> Optional[Candle]:
        """Find the latest candle for symbol and interval."""
        stmt = select(MarketPriceModel).where(
            and_(
                MarketPriceModel.symbol == symbol,
                MarketPriceModel.interval == interval.value
            )
        ).order_by(MarketPriceModel.timestamp.desc()).limit(1)
        
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        
        return self._model_to_domain(model) if model else None

    async def delete_old(self, older_than: datetime) -> int:
        """Delete candles older than specified date."""
        stmt = select(MarketPriceModel).where(
            MarketPriceModel.timestamp < older_than
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        
        count = len(models)
        for model in models:
            await self._session.delete(model)
        
        await self._session.flush()
        return count

    async def save_batch(self, candles: List[Candle]) -> None:
        """Save multiple candles."""
        try:
            for candle in candles:
                await self.save(candle)
            await self._session.flush()
        except Exception as e:
            await self._session.rollback()
            raise e

    async def get_ohlc_data(
        self,
        symbol: str,
        interval: CandleInterval,
        start_time: datetime,
        end_time: datetime
    ) -> List[Dict[str, Any]]:
        """Get OHLC data formatted for charting."""
        candles = await self.find_by_symbol_and_interval(
            symbol=symbol,
            interval=interval,
            start_time=start_time,
            end_time=end_time,
            limit=1000
        )
        
        return [
            {
                "timestamp": candle.open_time.isoformat() if candle.open_time else None,
                "open": float(candle.open_price),
                "high": float(candle.high_price),
                "low": float(candle.low_price),
                "close": float(candle.close_price),
                "volume": float(candle.volume) if candle.volume else 0
            }
            for candle in sorted(candles, key=lambda c: c.open_time)
        ]

    def _domain_to_model(self, candle: Candle) -> MarketPriceModel:
        """Convert domain entity to database model."""
        return MarketPriceModel(
            symbol=candle.symbol,
            exchange_id=1,  # Placeholder - should be mapped from exchange
            interval=candle.interval.value,
            timestamp=candle.open_time,
            open=candle.open_price,
            high=candle.high_price,
            low=candle.low_price,
            close=candle.close_price,
            volume=candle.volume,
            quote_volume=candle.quote_volume,
            num_trades=candle.trade_count,
            taker_buy_base_volume=candle.taker_buy_volume,
            taker_buy_quote_volume=candle.taker_buy_quote_volume
        )

    def _update_model_from_domain(self, model: MarketPriceModel, candle: Candle):
        """Update database model from domain entity."""
        model.open = candle.open_price
        model.high = candle.high_price
        model.low = candle.low_price
        model.close = candle.close_price
        model.volume = candle.volume
        model.quote_volume = candle.quote_volume
        model.num_trades = candle.trade_count
        model.taker_buy_base_volume = candle.taker_buy_volume
        model.taker_buy_quote_volume = candle.taker_buy_quote_volume

    def _model_to_domain(self, model: MarketPriceModel) -> Candle:
        """Convert database model to domain entity."""
        return Candle(
            symbol=model.symbol,
            interval=CandleInterval(model.interval),
            open_time=model.timestamp,
            close_time=model.timestamp,  # Calculate based on interval
            open_price=model.open,
            high_price=model.high,
            low_price=model.low,
            close_price=model.close,
            volume=model.volume,
            quote_volume=model.quote_volume or Decimal("0"),
            trade_count=model.num_trades or 0,
            taker_buy_volume=model.taker_buy_base_volume,
            taker_buy_quote_volume=model.taker_buy_quote_volume
        )


class OrderBookRepository(IOrderBookRepository):
    """SQLAlchemy implementation of order book repository."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def save(self, order_book: OrderBook) -> OrderBook:
        """Save an order book snapshot."""
        try:
            model = self._domain_to_model(order_book)
            self._session.add(model)
            await self._session.flush()
            await self._session.refresh(model)
            
            return self._model_to_domain(model)
        except Exception as e:
            await self._session.rollback()
            raise e

    async def find_latest(self, symbol: str) -> Optional[OrderBook]:
        """Find the latest order book for a symbol."""
        stmt = select(OrderBookSnapshotModel).where(
            OrderBookSnapshotModel.symbol == symbol
        ).order_by(OrderBookSnapshotModel.timestamp.desc()).limit(1)
        
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        
        return self._model_to_domain(model) if model else None

    async def find_by_symbol(
        self,
        symbol: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[OrderBook]:
        """Find order book snapshots by symbol within time range."""
        stmt = select(OrderBookSnapshotModel).where(
            OrderBookSnapshotModel.symbol == symbol
        )
        
        if start_time:
            stmt = stmt.where(OrderBookSnapshotModel.timestamp >= start_time)
        if end_time:
            stmt = stmt.where(OrderBookSnapshotModel.timestamp <= end_time)
            
        stmt = stmt.order_by(OrderBookSnapshotModel.timestamp.desc()).limit(limit)
        
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        
        return [self._model_to_domain(model) for model in models]

    async def delete_old(self, older_than: datetime) -> int:
        """Delete order book snapshots older than specified date."""
        stmt = select(OrderBookSnapshotModel).where(
            OrderBookSnapshotModel.timestamp < older_than
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        
        count = len(models)
        for model in models:
            await self._session.delete(model)
        
        await self._session.flush()
        return count

    def _domain_to_model(self, order_book: OrderBook) -> OrderBookSnapshotModel:
        """Convert domain entity to database model."""
        # Convert bid/ask lists to JSON format
        bids_json = [[str(level.price), str(level.quantity)] for level in order_book.bids]
        asks_json = [[str(level.price), str(level.quantity)] for level in order_book.asks]
        
        return OrderBookSnapshotModel(
            symbol=order_book.symbol,
            exchange_id=1,  # Placeholder
            timestamp=order_book.timestamp,
            bids=bids_json,
            asks=asks_json,
            total_bid_volume=sum(level.quantity for level in order_book.bids),
            total_ask_volume=sum(level.quantity for level in order_book.asks),
            spread=order_book.get_spread(),
            mid_price=order_book.get_mid_price()
        )

    def _model_to_domain(self, model: OrderBookSnapshotModel) -> OrderBook:
        """Convert database model to domain entity."""
        from ....domain.market_data import OrderBookLevel
        
        # Convert JSON to bid/ask levels
        bids = [
            OrderBookLevel(price=Decimal(level[0]), quantity=Decimal(level[1]))
            for level in (model.bids or [])
        ]
        asks = [
            OrderBookLevel(price=Decimal(level[0]), quantity=Decimal(level[1]))
            for level in (model.asks or [])
        ]
        
        return OrderBook(
            symbol=model.symbol,
            bids=bids,
            asks=asks,
            timestamp=model.timestamp,
            last_update_id=getattr(model, 'last_update_id', None)
        )


# Placeholder implementations for missing interfaces
class TickRepository(ITickRepository):
    """Placeholder tick repository implementation."""
    
    def __init__(self, session: AsyncSession):
        self._session = session
    
    async def save(self, tick: Tick) -> Tick:
        """Save tick data."""
        raise NotImplementedError("Tick repository not implemented yet")
    
    async def find_by_symbol(self, symbol: str, start_time: Optional[datetime] = None, end_time: Optional[datetime] = None, limit: int = 1000) -> List[Tick]:
        """Find ticks by symbol."""
        raise NotImplementedError("Tick repository not implemented yet")
    
    async def delete_old(self, older_than: datetime) -> int:
        """Delete old ticks."""
        raise NotImplementedError("Tick repository not implemented yet")


class TradeRepository(ITradeRepository):
    """Placeholder trade repository implementation."""
    
    def __init__(self, session: AsyncSession):
        self._session = session
    
    async def save(self, trade: Trade) -> Trade:
        """Save trade data."""
        raise NotImplementedError("Trade repository not implemented yet")
    
    async def find_by_symbol(self, symbol: str, start_time: Optional[datetime] = None, end_time: Optional[datetime] = None, limit: int = 1000) -> List[Trade]:
        """Find trades by symbol."""
        raise NotImplementedError("Trade repository not implemented yet")
    
    async def delete_old(self, older_than: datetime) -> int:
        """Delete old trades."""
        raise NotImplementedError("Trade repository not implemented yet")


class MarketStatsRepository(IMarketStatsRepository):
    """Placeholder market stats repository implementation."""
    
    def __init__(self, session: AsyncSession):
        self._session = session
    
    async def save(self, stats: MarketStats) -> MarketStats:
        """Save market stats."""
        raise NotImplementedError("Market stats repository not implemented yet")
    
    async def find_by_symbol(self, symbol: str) -> Optional[MarketStats]:
        """Find stats by symbol."""
        raise NotImplementedError("Market stats repository not implemented yet")
    
    async def find_all(self) -> List[MarketStats]:
        """Find all market stats."""
        raise NotImplementedError("Market stats repository not implemented yet")