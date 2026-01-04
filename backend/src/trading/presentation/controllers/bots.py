"""Bot management API endpoints."""
from typing import List, Optional
from uuid import UUID
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from ...application.use_cases.bot_use_cases import (
    CreateBotUseCase,
    StartBotUseCase,
    StopBotUseCase,
    PauseBotUseCase,
    ResumeBotUseCase,
    GetBotsUseCase,
    GetBotByIdUseCase,
    UpdateBotConfigurationUseCase,
    DeleteBotUseCase,
)
from ...domain.bot import BotStatus
from ...domain.bot import RiskLevel
from ...shared.exceptions import NotFoundError, ValidationError, BusinessException, DuplicateError
from ...interfaces.dependencies.auth import get_current_user
from ...interfaces.dependencies.providers import (
    get_create_bot_use_case,
    get_get_bots_use_case,
    get_get_bot_by_id_use_case,
    get_start_bot_use_case,
    get_stop_bot_use_case,
    get_pause_bot_use_case,
    get_resume_bot_use_case,
    get_update_bot_config_use_case,
    get_delete_bot_use_case,
    get_position_service
)
from ...application.services.position_service import PositionService


router = APIRouter(prefix="/bots", tags=["bots"])


# Request/Response Models
class CreateBotRequest(BaseModel):
    """Request model for creating a bot."""
    model_config = ConfigDict(from_attributes=True)
    
    name: str = Field(..., min_length=1, max_length=100)
    strategy_id: UUID
    exchange_connection_id: UUID
    symbol: str = Field(..., min_length=1, max_length=20)
    base_quantity: Optional[Decimal] = Field(None, description="Base asset quantity")
    quote_quantity: Optional[Decimal] = Field(None, description="Quote asset quantity")
    max_active_orders: int = Field(10, gt=0, le=100)
    risk_percentage: Decimal = Field(Decimal("1.0"), gt=0, le=100)
    take_profit_percentage: Decimal = Field(Decimal("2.0"), gt=0)
    stop_loss_percentage: Decimal = Field(Decimal("1.0"), gt=0)
    description: Optional[str] = Field(None, max_length=500)
    risk_level: RiskLevel = RiskLevel.MODERATE
    max_daily_loss: Optional[Decimal] = Field(None, gt=0)
    max_drawdown: Optional[Decimal] = Field(None, gt=0)
    strategy_settings: Optional[dict] = None
    configuration: Optional[dict] = None  # Allow configuration for compatibility
    bot_type: Optional[str] = None # Allow passing bot type for strategy selection


class UpdateBotConfigurationRequest(BaseModel):
    """Request model for updating bot configuration."""
    model_config = ConfigDict(from_attributes=True)
    
    symbol: Optional[str] = Field(None, min_length=1, max_length=20)
    base_quantity: Optional[Decimal] = Field(None, gt=0)
    quote_quantity: Optional[Decimal] = Field(None, gt=0)
    max_active_orders: Optional[int] = Field(None, gt=0, le=100)
    risk_percentage: Optional[Decimal] = Field(None, gt=0, le=100)
    take_profit_percentage: Optional[Decimal] = Field(None, gt=0)
    stop_loss_percentage: Optional[Decimal] = Field(None, gt=0)
    max_daily_loss: Optional[Decimal] = Field(None, gt=0)
    max_drawdown: Optional[Decimal] = Field(None, gt=0)
    strategy_settings: Optional[dict] = None


class BotResponse(BaseModel):
    """Response model for bot."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    user_id: UUID
    name: str
    strategy_id: UUID
    exchange_connection_id: UUID
    status: BotStatus
    description: Optional[str]
    risk_level: RiskLevel
    start_time: Optional[str]
    stop_time: Optional[str]
    last_error: Optional[str]
    active_orders_count: int
    daily_pnl: Decimal
    total_runtime_seconds: int
    created_at: str
    updated_at: str
    
    # Configuration
    symbol: str
    base_quantity: Decimal
    quote_quantity: Decimal
    max_active_orders: int
    risk_percentage: Decimal
    take_profit_percentage: Decimal
    stop_loss_percentage: Decimal
    max_daily_loss: Optional[Decimal]
    max_drawdown: Optional[Decimal]
    strategy_settings: dict
    
    # Performance
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_profit_loss: Decimal
    total_fees: Decimal
    net_profit_loss: Decimal
    max_drawdown_actual: Decimal
    
    # Streak Tracking
    current_win_streak: int = 0
    current_loss_streak: int = 0
    max_win_streak: int = 0
    max_loss_streak: int = 0


class StopBotRequest(BaseModel):
    """Request model for stopping a bot."""
    reason: Optional[str] = Field(None, max_length=500)


class PauseBotRequest(BaseModel):
    """Request model for pausing a bot."""
    reason: Optional[str] = Field(None, max_length=500)


def bot_to_response(bot) -> BotResponse:
    """Convert Bot entity to response model."""
    return BotResponse(
        id=bot.id,
        user_id=bot.user_id,
        name=bot.name,
        strategy_id=bot.strategy_id,
        exchange_connection_id=bot.exchange_connection_id,
        status=bot.status,
        description=bot.description,
        risk_level=bot.risk_level,
        start_time=bot.start_time.isoformat() if bot.start_time else None,
        stop_time=bot.stop_time.isoformat() if bot.stop_time else None,
        last_error=bot.last_error,
        active_orders_count=len(bot.active_orders),
        daily_pnl=bot.daily_pnl,
        total_runtime_seconds=bot.get_runtime_seconds(),
        created_at=bot.created_at.isoformat(),
        updated_at=bot.updated_at.isoformat(),
        
        # Configuration
        symbol=bot.configuration.symbol,
        base_quantity=bot.configuration.base_quantity,
        quote_quantity=bot.configuration.quote_quantity,
        max_active_orders=bot.configuration.max_active_orders,
        risk_percentage=bot.configuration.risk_percentage,
        take_profit_percentage=bot.configuration.take_profit_percentage,
        stop_loss_percentage=bot.configuration.stop_loss_percentage,
        max_daily_loss=bot.configuration.max_daily_loss,
        max_drawdown=bot.configuration.max_drawdown,
        strategy_settings=bot.configuration.strategy_settings,
        
        # Performance (Use recalculated cumulative stats, not stale JSONB)
        total_trades=bot.total_trades or bot.performance.total_trades,
        winning_trades=bot.winning_trades or bot.performance.winning_trades,
        losing_trades=bot.losing_trades or bot.performance.losing_trades,
        win_rate=((bot.winning_trades / max(bot.total_trades, 1)) * 100) if bot.total_trades else bot.performance.win_rate,
        total_profit_loss=bot.total_pnl or bot.performance.total_profit_loss,
        total_fees=bot.performance.total_fees,
        net_profit_loss=bot.total_pnl or bot.performance.net_profit_loss,
        max_drawdown_actual=bot.performance.max_drawdown,
        
        # Streak Tracking
        current_win_streak=bot.current_win_streak,
        current_loss_streak=bot.current_loss_streak,
        max_win_streak=bot.max_win_streak,
        max_loss_streak=bot.max_loss_streak,
    )


@router.post("/", response_model=BotResponse, status_code=status.HTTP_201_CREATED)
async def create_bot(
    request: CreateBotRequest,
    current_user = Depends(get_current_user),
    create_bot_use_case: CreateBotUseCase = Depends(get_create_bot_use_case),
):
    """Create a new bot."""
    print(f"DEBUG: create_bot payload: {request.model_dump()}")
    try:
        # Prepare settings and defaults
        settings = request.strategy_settings or {}
        if request.bot_type and "strategy_type" not in settings:
            settings["strategy_type"] = request.bot_type
            
        base_qty = request.base_quantity or Decimal(0)
        quote_qty = request.quote_quantity or Decimal(0)
        
        bot = await create_bot_use_case.execute(
            user_id=current_user.id,
            name=request.name,
            strategy_id=request.strategy_id,
            exchange_connection_id=request.exchange_connection_id,
            symbol=request.symbol,
            base_quantity=base_qty,
            quote_quantity=quote_qty,
            max_active_orders=request.max_active_orders,
            risk_percentage=request.risk_percentage,
            take_profit_percentage=request.take_profit_percentage,
            stop_loss_percentage=request.stop_loss_percentage,
            description=request.description,
            risk_level=request.risk_level,
            max_daily_loss=request.max_daily_loss,
            max_drawdown=request.max_drawdown,
            strategy_settings=settings,
        )
        return bot_to_response(bot)
    
    except DuplicateError as e:
        print(f"DEBUG: DuplicateError: {e}")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except (NotFoundError, ValidationError, ValueError) as e:
        print(f"DEBUG: ValidationError/ValueError: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/", response_model=List[BotResponse])
async def get_bots(
    status_filter: Optional[BotStatus] = None,
    current_user = Depends(get_current_user),
    get_bots_use_case: GetBotsUseCase = Depends(get_get_bots_use_case),
):
    """Get user's bots."""
    try:
        bots = await get_bots_use_case.execute(
            user_id=current_user.id,
            status=status_filter
        )
        
        # === SELF-HEALING: Recalculate stats for each bot ===
        # This ensures consistency between Bot Management and Bot Details pages
        from ...application.services.bot_stats_service import BotStatsService
        from ...infrastructure.persistence.database import AsyncSessionLocal
        import logging
        
        try:
            async with AsyncSessionLocal() as session:
                stats_service = BotStatsService(session)
                for bot in bots:
                    try:
                        await stats_service.update_stats_on_trade_close(str(bot.id), Decimal("0"))
                    except Exception as e:
                        logging.getLogger(__name__).warning(f"Stats recalc failed for bot {bot.id}: {e}")
        except Exception as stats_err:
            logging.getLogger(__name__).error(f"Stats recalculation session failed: {stats_err}")
        
        # Re-fetch bots to get updated stats
        bots = await get_bots_use_case.execute(
            user_id=current_user.id,
            status=status_filter
        )
        
        return [bot_to_response(bot) for bot in bots]
    
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{bot_id}", response_model=BotResponse)
async def get_bot(
    bot_id: UUID,
    current_user = Depends(get_current_user),
    get_bot_use_case: GetBotByIdUseCase = Depends(get_get_bot_by_id_use_case),
):
    """Get a specific bot."""
    from sqlalchemy.ext.asyncio import AsyncSession
    from ...infrastructure.persistence.database import get_db
    from ...application.services.bot_stats_service import BotStatsService
    
    try:
        bot = await get_bot_use_case.execute(
            user_id=current_user.id,
            bot_id=bot_id
        )
        
        # === SELF-HEALING: Recalculate stats from Trade table ===
        # This ensures that even if WebSocket updates failed, stats are always correct on page load.
        try:
            from ...interfaces.dependencies.providers import get_db as get_db_dep
            # Create a fresh session for recalculation
            from ...infrastructure.persistence.database import AsyncSessionLocal
            async with AsyncSessionLocal() as session:
                stats_service = BotStatsService(session)
                # Call update_stats with a dummy PnL of 0 to trigger RECALCULATION
                # (BotStatsService now uses self-healing aggregation instead of increments)
                await stats_service.update_stats_on_trade_close(str(bot_id), Decimal("0"))
        except Exception as stats_err:
            # Don't fail the request if stats recalc fails, just log
            import logging
            logging.getLogger(__name__).error(f"Stats recalculation failed: {stats_err}")
        
        # Re-fetch bot to get updated stats
        bot = await get_bot_use_case.execute(
            user_id=current_user.id,
            bot_id=bot_id
        )
        
        return bot_to_response(bot)
    
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{bot_id}/start", response_model=BotResponse)
async def start_bot(
    bot_id: UUID,
    current_user = Depends(get_current_user),
    start_bot_use_case: StartBotUseCase = Depends(get_start_bot_use_case),
):
    """Start a bot."""
    try:
        bot = await start_bot_use_case.execute(
            user_id=current_user.id,
            bot_id=bot_id
        )
        try:
            return bot_to_response(bot)
        except Exception as e:
            print(f"DEBUG: Response Serialization Error: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Serialization Error: {e}")
    
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except (ValidationError, BusinessException) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{bot_id}/stop", response_model=BotResponse)
async def stop_bot(
    bot_id: UUID,
    request: Optional[StopBotRequest] = None,
    current_user = Depends(get_current_user),
    stop_bot_use_case: StopBotUseCase = Depends(get_stop_bot_use_case),
):
    """Stop a bot."""
    try:
        reason = request.reason if request else None
        bot = await stop_bot_use_case.execute(
            user_id=current_user.id,
            bot_id=bot_id,
            reason=reason
        )
        return bot_to_response(bot)
    
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except (ValidationError, BusinessException) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{bot_id}/pause", response_model=BotResponse)
async def pause_bot(
    bot_id: UUID,
    request: Optional[PauseBotRequest] = None,
    current_user = Depends(get_current_user),
    pause_bot_use_case: PauseBotUseCase = Depends(get_pause_bot_use_case),
):
    """Pause a bot."""
    try:
        reason = request.reason if request else None
        bot = await pause_bot_use_case.execute(
            user_id=current_user.id,
            bot_id=bot_id,
            reason=reason
        )
        return bot_to_response(bot)
    
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except (ValidationError, BusinessException) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{bot_id}/resume", response_model=BotResponse)
async def resume_bot(
    bot_id: UUID,
    current_user = Depends(get_current_user),
    resume_bot_use_case: ResumeBotUseCase = Depends(get_resume_bot_use_case),
):
    """Resume a paused bot."""
    try:
        bot = await resume_bot_use_case.execute(
            user_id=current_user.id,
            bot_id=bot_id
        )
        return bot_to_response(bot)
    
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except (ValidationError, BusinessException) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put("/{bot_id}/configuration", response_model=BotResponse)
async def update_bot_configuration(
    bot_id: UUID,
    request: UpdateBotConfigurationRequest,
    current_user = Depends(get_current_user),
    update_bot_config_use_case: UpdateBotConfigurationUseCase = Depends(get_update_bot_config_use_case),
):
    """Update bot configuration."""
    try:
        bot = await update_bot_config_use_case.execute(
            user_id=current_user.id,
            bot_id=bot_id,
            symbol=request.symbol,
            base_quantity=request.base_quantity,
            quote_quantity=request.quote_quantity,
            max_active_orders=request.max_active_orders,
            risk_percentage=request.risk_percentage,
            take_profit_percentage=request.take_profit_percentage,
            stop_loss_percentage=request.stop_loss_percentage,
            max_daily_loss=request.max_daily_loss,
            max_drawdown=request.max_drawdown,
            strategy_settings=request.strategy_settings,
        )
        return bot_to_response(bot)
    
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except (ValidationError, BusinessException) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{bot_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bot(
    bot_id: UUID,
    current_user = Depends(get_current_user),
    delete_bot_use_case: DeleteBotUseCase = Depends(get_delete_bot_use_case),
):
    """Delete a bot."""
    try:
        await delete_bot_use_case.execute(
            user_id=current_user.id,
            bot_id=bot_id
        )
    
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except (ValidationError, BusinessException) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# Bot Resource APIs (Phase 1.3)
@router.get("/{bot_id}/positions")
async def get_bot_positions(
    bot_id: UUID,
    limit: int = 50,
    offset: int = 0,
    current_user = Depends(get_current_user),
    position_service: PositionService = Depends(get_position_service)
):
    """
    Get bot's open positions.
    FETCHES LIVE FROM EXCHANGE and syncs to DB.
    
    Returns list of positions.
    """
    try:
        result = await position_service.get_live_positions(bot_id)
        # TODO: Implement in-memory pagination if result['positions'] is huge (unlikely for < 50)
        return {
            "positions": result["positions"],
            "total": result["total"],
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        # Log and raise
        print(f"Error fetching positions: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))



class ClosePositionRequest(BaseModel):
    """Request model for closing a position."""
    symbol: str
    side: str = Field(..., description="LONG or SHORT")

@router.post("/{bot_id}/positions/close")
async def close_position(
    bot_id: UUID,
    request: ClosePositionRequest,
    current_user = Depends(get_current_user),
    position_service: PositionService = Depends(get_position_service)
):
    """
    Close a specific position for the bot.
    """
    try:
        return await position_service.close_position(
            bot_id=bot_id,
            symbol=request.symbol,
            side=request.side
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        print(f"Error closing position: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/{bot_id}/positions/close-all")
async def close_all_positions(
    bot_id: UUID,
    current_user = Depends(get_current_user),
    position_service: PositionService = Depends(get_position_service)
):
    """
    Close ALL open positions for the bot.
    """
    try:
        return await position_service.close_all_positions(bot_id)
    except Exception as e:
        print(f"Error closing all positions: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{bot_id}/orders")
async def get_bot_orders(
    bot_id: UUID,
    limit: int = 50,
    offset: int = 0,
    status_filter: Optional[str] = None,
    current_user = Depends(get_current_user),
):
    """
    Get bot's recent orders.
    
    Query Params:
        - limit: Page limit (default 50)
        - offset: Page offset (default 0)
        - status_filter: Filter by status (optional: PENDING, FILLED, CANCELLED)
    
    Returns paginated list of orders with:
        - id: Order UUID
        - symbol: Trading symbol
        - side: LONG or SHORT
        - type: Order type
        - quantity: Order quantity
        - price: Order price (null for market orders)
        - status: Order status
        - filled_quantity: Filled quantity
        - filled_avg_price: Average fill price
        - created_at: Creation timestamp
    """
    from ...infrastructure.persistence.database import get_db_context
    from sqlalchemy import select, and_, desc, func
    from ...infrastructure.persistence.models.trading_models import OrderModel
    
    async with get_db_context() as session:
        # Build where clause
        where_clauses = [
            OrderModel.bot_id == bot_id,
            OrderModel.deleted_at.is_(None)
        ]
        
        if status_filter:
            where_clauses.append(OrderModel.status == status_filter.upper())
        
        # Count total
        count_stmt = select(func.count(OrderModel.id)).where(and_(*where_clauses))
        count_result = await session.execute(count_stmt)
        total = count_result.scalar() or 0
        
        # Get orders
        stmt = select(OrderModel).where(
            and_(*where_clauses)
        ).order_by(
            desc(OrderModel.created_at)
        ).limit(limit).offset(offset)
        
        result = await session.execute(stmt)
        orders = result.scalars().all()
        
        orders_data = []
        for order in orders:
            orders_data.append({
                "id": str(order.id),
                "symbol": order.symbol,
                "side": order.side,
                "type": order.order_type,
                "quantity": float(order.quantity),
                "price": float(order.price) if order.price else None,
                "status": order.status,
                "filled_quantity": float(order.filled_quantity),
                "filled_avg_price": float(order.filled_avg_price) if order.filled_avg_price else None,
                "created_at": order.created_at.isoformat()
            })
        
        return {
            "orders": orders_data,
            "total": total,
            "limit": limit,
            "offset": offset
        }


@router.get("/{bot_id}/trades")
async def get_bot_trades(
    bot_id: UUID,
    limit: int = 50,
    offset: int = 0,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user = Depends(get_current_user),
):
    """
    Get bot's trade history.
    
    Query Params:
        - limit: Page limit (default 50)
        - offset: Page offset (default 0)
        - start_date: Start date filter (ISO format, optional)
        - end_date: End date filter (ISO format, optional)
    
    Returns paginated list of trades with:
        - id: Trade UUID
        - symbol: Trading symbol
        - side: LONG or SHORT
        - quantity: Trade quantity
        - price: Execution price
        - fee: Trading fee
        - realized_pnl: Realized P&L
        - created_at: Execution timestamp
    """
    from ...infrastructure.persistence.database import get_db_context
    from sqlalchemy import select, and_, desc, func
    from ...infrastructure.persistence.models.trading_models import TradeModel
    from datetime import datetime
    
    async with get_db_context() as session:
        # Build where clause
        where_clauses = [
            TradeModel.bot_id == bot_id
            # TradeModel is immutable, no deleted_at
        ]
        
        if start_date:
            where_clauses.append(TradeModel.executed_at >= datetime.fromisoformat(start_date))
        
        if end_date:
            where_clauses.append(TradeModel.executed_at <= datetime.fromisoformat(end_date))
        
        # Count total
        count_stmt = select(func.count(TradeModel.id)).where(and_(*where_clauses))
        count_result = await session.execute(count_stmt)
        total = count_result.scalar() or 0
        
        # Get trades
        stmt = select(TradeModel).where(
            and_(*where_clauses)
        ).order_by(
            desc(TradeModel.executed_at)
        ).limit(limit).offset(offset)
        
        result = await session.execute(stmt)
        trades = result.scalars().all()
        
        trades_data = []
        for trade in trades:
            trades_data.append({
                "id": str(trade.id),
                "symbol": trade.symbol,
                "side": trade.side,
                "quantity": float(trade.quantity),
                "price": float(trade.price),
                "fee": float(trade.fee or 0),
                "realized_pnl": float(trade.pnl or 0),
                "created_at": trade.executed_at.isoformat()
            })
        
        return {
            "trades": trades_data,
            "total": total,
            "limit": limit,
            "offset": offset
        }