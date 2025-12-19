"""Bot API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import uuid

from .schemas.bot import (
    CreateBotRequest,
    UpdateBotRequest,
    BotResponse,
    BotListResponse,
    BotActionResponse,
    BotConfigurationResponse,
    BotMetricsResponse,
)
from ....infrastructure.persistence.database import get_db
from ....infrastructure.repositories.bot_repository import BotRepository
from ...dependencies.auth import get_current_active_user
from ....domain.user import User
from ....domain.bot import (
    Bot,
    BotType,
    BotConfiguration,
    BotStatus,
)


router = APIRouter(prefix="/bots", tags=["Bots"])


def _to_bot_response(bot: Bot) -> BotResponse:
    """Convert Bot entity to response."""
    return BotResponse(
        id=bot.id,
        user_id=bot.user_id,
        name=bot.name,
        description=bot.description,
        configuration=BotConfigurationResponse(
            bot_type=bot.configuration.bot_type.value,
            symbol=bot.configuration.symbol,
            exchange_connection_id=bot.configuration.exchange_connection_id,
            max_position_size=bot.configuration.max_position_size,
            max_open_orders=bot.configuration.max_open_orders,
            leverage=bot.configuration.leverage,
            strategy_params=bot.configuration.strategy_params,
            stop_loss_pct=bot.configuration.stop_loss_pct,
            take_profit_pct=bot.configuration.take_profit_pct,
            max_daily_loss=bot.configuration.max_daily_loss,
        ),
        status=bot.status.value,
        is_active=bot.is_active,
        metrics=BotMetricsResponse(
            total_trades=bot.metrics.total_trades,
            winning_trades=bot.metrics.winning_trades,
            losing_trades=bot.metrics.losing_trades,
            total_profit=bot.metrics.total_profit,
            total_loss=bot.metrics.total_loss,
            net_profit=bot.metrics.net_profit,
            win_rate=bot.metrics.win_rate,
            avg_profit=bot.metrics.avg_profit,
            avg_loss=bot.metrics.avg_loss,
            max_drawdown=bot.metrics.max_drawdown,
            profit_factor=bot.metrics.profit_factor,
            sharpe_ratio=bot.metrics.sharpe_ratio,
        ),
        started_at=bot.started_at,
        stopped_at=bot.stopped_at,
        last_trade_at=bot.last_trade_at,
        error_message=bot.error_message,
        created_at=bot.created_at,
        updated_at=bot.updated_at,
    )


@router.post("/", response_model=BotResponse, status_code=status.HTTP_201_CREATED)
async def create_bot(
    request: CreateBotRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new trading bot.
    
    Args:
        request: Bot creation request
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        Created bot
    """
    bot_repo = BotRepository(db)
    
    # Create bot configuration
    try:
        configuration = BotConfiguration(
            bot_type=BotType(request.configuration.bot_type),
            symbol=request.configuration.symbol,
            exchange_connection_id=request.configuration.exchange_connection_id,
            max_position_size=request.configuration.max_position_size,
            max_open_orders=request.configuration.max_open_orders,
            leverage=request.configuration.leverage,
            strategy_params=request.configuration.strategy_params,
            stop_loss_pct=request.configuration.stop_loss_pct,
            take_profit_pct=request.configuration.take_profit_pct,
            max_daily_loss=request.configuration.max_daily_loss,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid bot configuration: {str(e)}",
        )
    
    # Create bot entity
    try:
        bot = Bot.create(
            user_id=current_user.id,
            name=request.name,
            configuration=configuration,
            description=request.description,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    
    # Save to database
    await bot_repo.save(bot)
    await db.commit()
    
    return _to_bot_response(bot)


@router.get("/", response_model=BotListResponse)
async def list_bots(
    status_filter: str = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all bots for current user.
    
    Args:
        status_filter: Optional status filter (RUNNING, STOPPED, etc.)
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        List of bots
    """
    bot_repo = BotRepository(db)
    
    if status_filter:
        try:
            status_enum = BotStatus(status_filter)
            bots = await bot_repo.find_by_status(current_user.id, status_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status_filter}",
            )
    else:
        bots = await bot_repo.find_by_user(current_user.id)
    
    return BotListResponse(
        bots=[_to_bot_response(bot) for bot in bots],
        total=len(bots),
    )


@router.get("/{bot_id}", response_model=BotResponse)
async def get_bot(
    bot_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get bot by ID.
    
    Args:
        bot_id: Bot ID
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        Bot details
    """
    bot_repo = BotRepository(db)
    
    try:
        bot = await bot_repo.find_by_id(uuid.UUID(bot_id))
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid bot ID format",
        )
    
    if not bot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bot not found",
        )
    
    # Verify ownership
    if bot.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this bot",
        )
    
    return _to_bot_response(bot)


@router.patch("/{bot_id}", response_model=BotResponse)
async def update_bot(
    bot_id: str,
    request: UpdateBotRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update bot details.
    
    Args:
        bot_id: Bot ID
        request: Update request
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        Updated bot
    """
    bot_repo = BotRepository(db)
    
    try:
        bot = await bot_repo.find_by_id(uuid.UUID(bot_id))
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid bot ID format",
        )
    
    if not bot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bot not found",
        )
    
    # Verify ownership
    if bot.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this bot",
        )
    
    # Update name/description
    if request.name:
        bot.name = request.name
    if request.description is not None:
        bot.description = request.description
    
    # Update configuration
    if request.configuration:
        try:
            new_config = BotConfiguration(
                bot_type=BotType(request.configuration.bot_type),
                symbol=request.configuration.symbol,
                exchange_connection_id=request.configuration.exchange_connection_id,
                max_position_size=request.configuration.max_position_size,
                max_open_orders=request.configuration.max_open_orders,
                leverage=request.configuration.leverage,
                strategy_params=request.configuration.strategy_params,
                stop_loss_pct=request.configuration.stop_loss_pct,
                take_profit_pct=request.configuration.take_profit_pct,
                max_daily_loss=request.configuration.max_daily_loss,
            )
            bot.update_configuration(new_config)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )
    
    # Save changes
    await bot_repo.save(bot)
    await db.commit()
    
    return _to_bot_response(bot)


@router.post("/{bot_id}/start", response_model=BotActionResponse)
async def start_bot(
    bot_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Start a bot.
    
    Args:
        bot_id: Bot ID
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        Action result
    """
    bot_repo = BotRepository(db)
    
    try:
        bot = await bot_repo.find_by_id(uuid.UUID(bot_id))
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid bot ID format",
        )
    
    if not bot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bot not found",
        )
    
    # Verify ownership
    if bot.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to start this bot",
        )
    
    # Start bot
    try:
        bot.start()
        await bot_repo.save(bot)
        await db.commit()
        
        return BotActionResponse(
            success=True,
            message="Bot started successfully",
            bot=_to_bot_response(bot),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/{bot_id}/stop", response_model=BotActionResponse)
async def stop_bot(
    bot_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Stop a bot.
    
    Args:
        bot_id: Bot ID
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        Action result
    """
    bot_repo = BotRepository(db)
    
    try:
        bot = await bot_repo.find_by_id(uuid.UUID(bot_id))
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid bot ID format",
        )
    
    if not bot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bot not found",
        )
    
    # Verify ownership
    if bot.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to stop this bot",
        )
    
    # Stop bot
    try:
        bot.stop()
        await bot_repo.save(bot)
        await db.commit()
        
        return BotActionResponse(
            success=True,
            message="Bot stopped successfully",
            bot=_to_bot_response(bot),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/{bot_id}/pause", response_model=BotActionResponse)
async def pause_bot(
    bot_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Pause a running bot.
    
    Args:
        bot_id: Bot ID
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        Action result
    """
    bot_repo = BotRepository(db)
    
    try:
        bot = await bot_repo.find_by_id(uuid.UUID(bot_id))
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid bot ID format",
        )
    
    if not bot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bot not found",
        )
    
    # Verify ownership
    if bot.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to pause this bot",
        )
    
    # Pause bot
    try:
        bot.pause()
        await bot_repo.save(bot)
        await db.commit()
        
        return BotActionResponse(
            success=True,
            message="Bot paused successfully",
            bot=_to_bot_response(bot),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/{bot_id}/resume", response_model=BotActionResponse)
async def resume_bot(
    bot_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Resume a paused bot.
    
    Args:
        bot_id: Bot ID
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        Action result
    """
    bot_repo = BotRepository(db)
    
    try:
        bot = await bot_repo.find_by_id(uuid.UUID(bot_id))
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid bot ID format",
        )
    
    if not bot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bot not found",
        )
    
    # Verify ownership
    if bot.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to resume this bot",
        )
    
    # Resume bot
    try:
        bot.resume()
        await bot_repo.save(bot)
        await db.commit()
        
        return BotActionResponse(
            success=True,
            message="Bot resumed successfully",
            bot=_to_bot_response(bot),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete("/{bot_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bot(
    bot_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a bot (soft delete).
    
    Args:
        bot_id: Bot ID
        current_user: Current authenticated user
        db: Database session
    """
    bot_repo = BotRepository(db)
    
    try:
        bot = await bot_repo.find_by_id(uuid.UUID(bot_id))
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid bot ID format",
        )
    
    if not bot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bot not found",
        )
    
    # Verify ownership
    if bot.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this bot",
        )
    
    # Cannot delete running bot
    if bot.status == BotStatus.RUNNING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete a running bot. Stop it first.",
        )
    
    # Soft delete
    await bot_repo.delete(uuid.UUID(bot_id))
    await db.commit()
