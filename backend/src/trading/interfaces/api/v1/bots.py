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
    # Map domain configuration to API configuration response
    config = bot.configuration
    config_response = BotConfigurationResponse(
        bot_type=config.bot_type.value if config.bot_type else "GRID",
        symbol=config.symbol,
        exchange_connection_id=bot.exchange_connection_id,  # From bot, not config
        max_position_size=float(config.base_quantity or config.quote_quantity),
        max_open_orders=config.max_active_orders,
        leverage=1,  # Default leverage
        strategy_params=config.strategy_settings,
        stop_loss_pct=float(config.stop_loss_percentage),
        take_profit_pct=float(config.take_profit_percentage),
        max_daily_loss=float(config.max_daily_loss) if config.max_daily_loss else None,
    )
    
    # Map domain performance to API metrics response
    perf = bot.performance
    metrics_response = BotMetricsResponse(
        total_trades=perf.total_trades,
        winning_trades=perf.winning_trades,
        losing_trades=perf.losing_trades,
        total_profit=float(perf.total_profit_loss) if perf.total_profit_loss > 0 else 0,
        total_loss=float(abs(perf.total_profit_loss)) if perf.total_profit_loss < 0 else 0,
        net_profit=float(perf.total_profit_loss),
        win_rate=perf.winning_trades / perf.total_trades * 100 if perf.total_trades > 0 else 0,
        avg_profit=0,  # Not tracked in domain
        avg_loss=0,    # Not tracked in domain
        max_drawdown=float(perf.max_drawdown),
        profit_factor=0,  # Not tracked in domain
        sharpe_ratio=float(perf.sharpe_ratio) if perf.sharpe_ratio else None,
    )
    
    return BotResponse(
        id=bot.id,
        user_id=bot.user_id,
        name=bot.name,
        description=bot.description,
        strategy_id=bot.strategy_id,
        configuration=config_response,
        status=bot.status.value,
        is_active=bot.is_active(),
        metrics=metrics_response,
        started_at=bot.start_time,
        stopped_at=bot.stop_time,
        last_trade_at=None,  # Not tracked in domain
        error_message=bot.last_error,
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
            strategy_id=request.strategy_id,
            exchange_connection_id=request.configuration.exchange_connection_id,
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
    # Use BotManager for execution (optional - may not be initialized)
    from ....application.services.bot_manager import get_bot_manager
    from ....application.use_cases.bot_use_cases import StartBotUseCase
    
    try:
        # Try to get bot manager, but it's optional for basic status update
        try:
            bot_manager = get_bot_manager()
        except RuntimeError:
            bot_manager = None  # Manager not initialized, will just update DB status
        
        bot_repo = BotRepository(db)
        use_case = StartBotUseCase(bot_repo, bot_manager)
        
        updated_bot = await use_case.execute(current_user.id, uuid.UUID(bot_id))
        
        return BotActionResponse(
            success=True,
            message="Bot started successfully",
            bot=_to_bot_response(updated_bot),
        )
    except Exception as e:
        status_code = status.HTTP_400_BAD_REQUEST
        if "not found" in str(e).lower():
            status_code = status.HTTP_404_NOT_FOUND
        elif "not authorized" in str(e).lower():
            status_code = status.HTTP_403_FORBIDDEN
            
        raise HTTPException(
            status_code=status_code,
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
    # Use BotManager for execution (optional - may not be initialized)
    from ....application.services.bot_manager import get_bot_manager
    from ....application.use_cases.bot_use_cases import StopBotUseCase
    
    try:
        # Try to get bot manager, but it's optional for basic status update
        try:
            bot_manager = get_bot_manager()
        except RuntimeError:
            bot_manager = None  # Manager not initialized, will just update DB status
        
        bot_repo = BotRepository(db)
        use_case = StopBotUseCase(bot_repo, bot_manager)
        
        updated_bot = await use_case.execute(current_user.id, uuid.UUID(bot_id))
        
        return BotActionResponse(
            success=True,
            message="Bot stopped successfully",
            bot=_to_bot_response(updated_bot),
        )
    except Exception as e:
        status_code = status.HTTP_400_BAD_REQUEST
        if "not found" in str(e).lower():
            status_code = status.HTTP_404_NOT_FOUND
        elif "not authorized" in str(e).lower():
            status_code = status.HTTP_403_FORBIDDEN
            
        raise HTTPException(
            status_code=status_code,
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
