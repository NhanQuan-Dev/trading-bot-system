"""Market data API endpoints."""
from typing import List, Optional, Dict, Any
from datetime import datetime as dt, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, ConfigDict, Field

from ...application.use_cases.market_data_use_cases import (
    CreateMarketDataSubscriptionUseCase,
    GetMarketDataSubscriptionsUseCase,
    GetMarketDataSubscriptionUseCase,
    DeleteMarketDataSubscriptionUseCase,
    GetCandleDataUseCase,
    GetOHLCDataUseCase,
    GetTickDataUseCase,
    GetLatestPriceUseCase,
    GetTradeDataUseCase,
    GetOrderBookUseCase,
    GetMarketStatsUseCase,
    GetMarketOverviewUseCase,
)
from ...domain.market_data import DataType, CandleInterval, StreamStatus
from ...shared.exceptions import NotFoundError, ValidationError, DuplicateError
from ...interfaces.dependencies.auth import get_current_user
from ...interfaces.dependencies.providers import (
    get_create_market_data_subscription_use_case,
    get_get_market_data_subscriptions_use_case,
    get_get_market_data_subscription_use_case,
    get_delete_market_data_subscription_use_case,
    get_get_candle_data_use_case,
    get_get_ohlc_data_use_case,
    get_get_tick_data_use_case,
    get_get_latest_price_use_case,
    get_get_trade_data_use_case,
    get_get_order_book_use_case,
    get_get_market_stats_use_case,
    get_get_market_overview_use_case,
)



import logging

logger = logging.getLogger(__name__)

# Lazy handler registration
_handler_registered = False

def ensure_handler_registered(binance_adapter, candle_repo):
    """Ensure fetch_missing_candles handler is registered."""
    global _handler_registered
    if not _handler_registered:
        from ...infrastructure.jobs.job_worker import JobWorker
        from ...infrastructure.jobs.fetch_missing_candles_job import FetchMissingCandlesJobV2
        handler = FetchMissingCandlesJobV2(binance_adapter, candle_repo)
        JobWorker.register_handler("fetch_missing_candles", handler.execute)
        _handler_registered = True
        logger.info("Registered fetch_missing_candles handler")

router = APIRouter(prefix="/market-data", tags=["market-data"])


# Request/Response Models
class CreateSubscriptionRequest(BaseModel):
    """Request model for creating market data subscription."""
    model_config = ConfigDict(from_attributes=True)
    
    symbol: str = Field(..., min_length=1, max_length=20)
    data_types: List[DataType] = Field(..., min_items=1)
    intervals: List[CandleInterval] = Field(default_factory=list)
    exchange: str = Field(default="BINANCE", max_length=20)


class SubscriptionResponse(BaseModel):
    """Response model for subscription."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    user_id: UUID
    symbol: str
    data_types: List[DataType]
    intervals: List[CandleInterval]
    status: StreamStatus
    exchange: str
    stream_url: Optional[str]
    last_message_at: Optional[str]
    error_message: Optional[str]
    reconnect_count: int
    created_at: str
    updated_at: str


class CandleResponse(BaseModel):
    """Response model for candle data."""
    model_config = ConfigDict(from_attributes=True)
    
    symbol: str
    interval: CandleInterval
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: float
    quote_volume: float
    open_time: str
    close_time: str
    trade_count: int
    price_change: float
    price_change_percent: float


class TickResponse(BaseModel):
    """Response model for tick data."""
    model_config = ConfigDict(from_attributes=True)
    
    symbol: str
    price: float
    size: float
    timestamp: str
    trade_id: Optional[str]
    is_buyer_maker: Optional[bool]


class TradeResponse(BaseModel):
    """Response model for trade data."""
    model_config = ConfigDict(from_attributes=True)
    
    symbol: str
    trade_id: str
    price: float
    quantity: float
    quote_quantity: float
    timestamp: str
    is_buyer_maker: bool
    trade_type: str


class OrderBookLevel(BaseModel):
    """Response model for order book level."""
    price: float
    quantity: float


class OrderBookResponse(BaseModel):
    """Response model for order book."""
    model_config = ConfigDict(from_attributes=True)
    
    symbol: str
    bids: List[OrderBookLevel]
    asks: List[OrderBookLevel]
    timestamp: str
    best_bid_price: Optional[float]
    best_ask_price: Optional[float]
    spread: Optional[float]
    spread_percent: Optional[float]
    mid_price: Optional[float]


def subscription_to_response(subscription) -> SubscriptionResponse:
    """Convert subscription entity to response model."""
    return SubscriptionResponse(
        id=subscription.id,
        user_id=subscription.user_id,
        symbol=subscription.symbol,
        data_types=subscription.data_types,
        intervals=subscription.intervals,
        status=subscription.status,
        exchange=subscription.exchange,
        stream_url=subscription.stream_url,
        last_message_at=subscription.last_message_at.isoformat() if subscription.last_message_at else None,
        error_message=subscription.error_message,
        reconnect_count=subscription.reconnect_count,
        created_at=subscription.created_at.isoformat(),
        updated_at=subscription.updated_at.isoformat(),
    )


def candle_to_response(candle) -> CandleResponse:
    """Convert candle entity to response model."""
    return CandleResponse(
        symbol=candle.symbol,
        interval=candle.interval,
        open_price=float(candle.open_price),
        high_price=float(candle.high_price),
        low_price=float(candle.low_price),
        close_price=float(candle.close_price),
        volume=float(candle.volume),
        quote_volume=float(candle.quote_volume),
        open_time=candle.open_time.isoformat(),
        close_time=candle.close_time.isoformat(),
        trade_count=candle.trade_count,
        price_change=float(candle.price_change),
        price_change_percent=float(candle.price_change_percent),
    )


def tick_to_response(tick) -> TickResponse:
    """Convert tick entity to response model."""
    return TickResponse(
        symbol=tick.symbol,
        price=float(tick.price),
        size=float(tick.size),
        timestamp=tick.timestamp.isoformat(),
        trade_id=tick.trade_id,
        is_buyer_maker=tick.is_buyer_maker,
    )


def trade_to_response(trade) -> TradeResponse:
    """Convert trade entity to response model."""
    return TradeResponse(
        symbol=trade.symbol,
        trade_id=trade.trade_id,
        price=float(trade.price),
        quantity=float(trade.quantity),
        quote_quantity=float(trade.quote_quantity),
        timestamp=trade.timestamp.isoformat(),
        is_buyer_maker=trade.is_buyer_maker,
        trade_type=trade.trade_type,
    )


def orderbook_to_response(orderbook) -> OrderBookResponse:
    """Convert order book entity to response model."""
    return OrderBookResponse(
        symbol=orderbook.symbol,
        bids=[
            OrderBookLevel(price=float(level.price), quantity=float(level.quantity))
            for level in orderbook.bids
        ],
        asks=[
            OrderBookLevel(price=float(level.price), quantity=float(level.quantity))
            for level in orderbook.asks
        ],
        timestamp=orderbook.timestamp.isoformat(),
        best_bid_price=float(orderbook.best_bid_price) if orderbook.best_bid_price else None,
        best_ask_price=float(orderbook.best_ask_price) if orderbook.best_ask_price else None,
        spread=float(orderbook.spread) if orderbook.spread else None,
        spread_percent=float(orderbook.spread_percent) if orderbook.spread_percent else None,
        mid_price=float(orderbook.mid_price) if orderbook.mid_price else None,
    )


# Subscription Management Endpoints
@router.post("/subscriptions", response_model=SubscriptionResponse, status_code=status.HTTP_201_CREATED)
async def create_subscription(
    request: CreateSubscriptionRequest,
    current_user = Depends(get_current_user),
    create_subscription_use_case: CreateMarketDataSubscriptionUseCase = Depends(get_create_market_data_subscription_use_case),
):
    """Create a new market data subscription."""
    try:
        subscription = await create_subscription_use_case.execute(
            user_id=current_user.id,
            symbol=request.symbol,
            data_types=request.data_types,
            intervals=request.intervals,
            exchange=request.exchange,
        )
        return subscription_to_response(subscription)
    
    except DuplicateError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/subscriptions", response_model=List[SubscriptionResponse])
async def get_subscriptions(
    current_user = Depends(get_current_user),
    get_subscriptions_use_case: GetMarketDataSubscriptionsUseCase = Depends(get_get_market_data_subscriptions_use_case),
):
    """Get user's market data subscriptions."""
    try:
        subscriptions = await get_subscriptions_use_case.execute(current_user.id)
        return [subscription_to_response(sub) for sub in subscriptions]
    
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/subscriptions/{subscription_id}", response_model=SubscriptionResponse)
async def get_subscription(
    subscription_id: UUID,
    current_user = Depends(get_current_user),
    get_subscription_use_case: GetMarketDataSubscriptionUseCase = Depends(get_get_market_data_subscription_use_case),
):
    """Get a specific subscription."""
    try:
        subscription = await get_subscription_use_case.execute(current_user.id, subscription_id)
        return subscription_to_response(subscription)
    
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/subscriptions/{subscription_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_subscription(
    subscription_id: UUID,
    current_user = Depends(get_current_user),
    delete_subscription_use_case: DeleteMarketDataSubscriptionUseCase = Depends(get_delete_market_data_subscription_use_case),
):
    """Delete a subscription."""
    try:
        await delete_subscription_use_case.execute(current_user.id, subscription_id)
    
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# Market Data Endpoints
@router.get("/candles/{symbol}", response_model=List[CandleResponse])
async def get_candles(
    symbol: str,
    interval: CandleInterval = Query(...),
    start_time: Optional[dt] = Query(None),
    end_time: Optional[dt] = Query(None),
    limit: Optional[int] = Query(None, ge=1, description="Maximum number of candles to return (no upper limit)"),
    repair: bool = Query(False, description="Attempt to repair missing data gaps"),
    get_candles_use_case: GetCandleDataUseCase = Depends(get_get_candle_data_use_case),
):
    """Get candle data for a symbol."""
    # @cache_response(ttl=60)
    # Ensure background job handler is registered
    from ...infrastructure.exchange.binance_adapter import BinanceAdapter
    from ...infrastructure.persistence.repositories.market_data_repository import CandleRepository
    from ...infrastructure.persistence.database import get_db_context
    
    # Lazy registration with dependencies
    async with get_db_context() as session:
        binance = BinanceAdapter(api_key="", api_secret="")  # Public endpoints don't need keys
        repo = CandleRepository(session)
        ensure_handler_registered(binance, repo)
    
    try:
        candles = await get_candles_use_case.execute(
            symbol=symbol.upper(),
            interval=interval,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            repair=repair
        )
        return [candle_to_response(candle) for candle in candles]
    
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/ohlc/{symbol}")
async def get_ohlc_data(
    symbol: str,
    interval: CandleInterval = Query(...),
    start_time: dt = Query(...),
    end_time: dt = Query(...),
    get_ohlc_use_case: GetOHLCDataUseCase = Depends(get_get_ohlc_data_use_case),
):
    """Get OHLC data formatted for charting."""
    try:
        data = await get_ohlc_use_case.execute(
            symbol=symbol.upper(),
            interval=interval,
            start_time=start_time,
            end_time=end_time,
        )
        return {"symbol": symbol.upper(), "interval": interval, "data": data}
    
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/ticks/{symbol}", response_model=List[TickResponse])
async def get_ticks(
    symbol: str,
    start_time: Optional[dt] = Query(None),
    end_time: Optional[dt] = Query(None),
    limit: Optional[int] = Query(None, ge=1, le=1000),
    get_ticks_use_case: GetTickDataUseCase = Depends(get_get_tick_data_use_case),
):
    """Get tick data for a symbol."""
    try:
        ticks = await get_ticks_use_case.execute(
            symbol=symbol.upper(),
            start_time=start_time,
            end_time=end_time,
            limit=limit,
        )
        return [tick_to_response(tick) for tick in ticks]
    
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/price/{symbol}")
async def get_latest_price(
    symbol: str,
    get_latest_price_use_case: GetLatestPriceUseCase = Depends(get_get_latest_price_use_case),
):
    """Get latest price data for a symbol."""
    try:
        data = await get_latest_price_use_case.execute(symbol.upper())
        return data
    
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/trades/{symbol}", response_model=List[TradeResponse])
async def get_trades(
    symbol: str,
    start_time: Optional[dt] = Query(None),
    end_time: Optional[dt] = Query(None),
    limit: Optional[int] = Query(None, ge=1, le=1000),
    get_trades_use_case: GetTradeDataUseCase = Depends(get_get_trade_data_use_case),
):
    """Get trade data for a symbol."""
    try:
        trades = await get_trades_use_case.execute(
            symbol=symbol.upper(),
            start_time=start_time,
            end_time=end_time,
            limit=limit,
        )
        return [trade_to_response(trade) for trade in trades]
    
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/orderbook/{symbol}", response_model=OrderBookResponse)
async def get_orderbook(
    symbol: str,
    get_orderbook_use_case: GetOrderBookUseCase = Depends(get_get_order_book_use_case),
):
    """Get latest order book for a symbol."""
    try:
        orderbook = await get_orderbook_use_case.execute(symbol.upper())
        if not orderbook:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order book not found")
        
        return orderbook_to_response(orderbook)
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/stats/{symbol}")
async def get_market_stats(
    symbol: str,
    get_stats_use_case: GetMarketStatsUseCase = Depends(get_get_market_stats_use_case),
):
    """Get market statistics for a symbol."""
    try:
        data = await get_stats_use_case.execute(symbol.upper())
        return data
    
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/stats")
async def get_all_market_stats(
    get_stats_use_case: GetMarketStatsUseCase = Depends(get_get_market_stats_use_case),
):
    """Get market statistics for all symbols."""
    try:
        data = await get_stats_use_case.execute()
        return data
    
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/overview")
async def get_market_overview(
    limit: int = Query(10, ge=1, le=50),
    get_overview_use_case: GetMarketOverviewUseCase = Depends(get_get_market_overview_use_case),
):
    """Get market overview with top movers."""
    try:
        data = await get_overview_use_case.execute(limit)
        return data
    
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# WebSocket Endpoint for Real-time Data
@router.websocket("/ws/{symbol}")
async def websocket_market_data(
    websocket: WebSocket,
    symbol: str,
    data_types: List[DataType] = Query(...),
):
    """WebSocket endpoint for real-time market data."""
    await websocket.accept()
    
    try:
        # Send initial connection message
        await websocket.send_json({
            "type": "connection",
            "status": "connected",
            "symbol": symbol.upper(),
            "data_types": data_types,
            "timestamp": dt.now().isoformat()
        })
        
        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Wait for messages from client
                data = await websocket.receive_text()
                
                # Echo back for now (in real implementation, this would stream live data)
                await websocket.send_json({
                    "type": "echo",
                    "message": data,
                    "timestamp": dt.now().isoformat()
                })
                
            except WebSocketDisconnect:
                break
                
    except Exception as e:
        await websocket.send_json({
            "type": "error", 
            "message": str(e),
            "timestamp": dt.now().isoformat()
        })
        await websocket.close(code=1000)


# Available Data Types and Intervals
@router.get("/data-types")
async def get_data_types():
    """Get available data types."""
    return [
        {
            "type": DataType.TICK,
            "name": "Tick Data",
            "description": "Individual price ticks and trade executions"
        },
        {
            "type": DataType.CANDLE,
            "name": "Candle Data",
            "description": "OHLCV candlestick data at various intervals"
        },
        {
            "type": DataType.ORDER_BOOK,
            "name": "Order Book",
            "description": "Order book depth with bid/ask levels"
        },
        {
            "type": DataType.TRADE,
            "name": "Trade Data",
            "description": "Individual trade execution data"
        },
        {
            "type": DataType.FUNDING_RATE,
            "name": "Funding Rate",
            "description": "Futures funding rate data"
        },
        {
            "type": DataType.MARK_PRICE,
            "name": "Mark Price",
            "description": "Mark price for futures contracts"
        },
    ]


@router.get("/intervals")
async def get_intervals():
    """Get available candle intervals."""
    return [
        {"interval": CandleInterval.ONE_MINUTE, "description": "1 minute"},
        {"interval": CandleInterval.THREE_MINUTE, "description": "3 minutes"},
        {"interval": CandleInterval.FIVE_MINUTE, "description": "5 minutes"},
        {"interval": CandleInterval.FIFTEEN_MINUTE, "description": "15 minutes"},
        {"interval": CandleInterval.THIRTY_MINUTE, "description": "30 minutes"},
        {"interval": CandleInterval.ONE_HOUR, "description": "1 hour"},
        {"interval": CandleInterval.TWO_HOUR, "description": "2 hours"},
        {"interval": CandleInterval.FOUR_HOUR, "description": "4 hours"},
        {"interval": CandleInterval.SIX_HOUR, "description": "6 hours"},
        {"interval": CandleInterval.EIGHT_HOUR, "description": "8 hours"},
        {"interval": CandleInterval.TWELVE_HOUR, "description": "12 hours"},
        {"interval": CandleInterval.ONE_DAY, "description": "1 day"},
        {"interval": CandleInterval.THREE_DAY, "description": "3 days"},
        {"interval": CandleInterval.ONE_WEEK, "description": "1 week"},
        {"interval": CandleInterval.ONE_MONTH, "description": "1 month"},
    ]