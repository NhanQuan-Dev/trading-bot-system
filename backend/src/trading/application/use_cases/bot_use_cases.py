"""Bot use cases."""
from typing import Optional, List
from uuid import UUID
from decimal import Decimal

from ...shared.exceptions import (
    NotFoundError, 
    ValidationError, 
    BusinessException,
    DuplicateError
)
from ...domain.bot import Bot, BotConfiguration, BotStatus, RiskLevel
from ...domain.bot.repository import IBotRepository, IStrategyRepository
from ...domain.exchange.repository import IExchangeRepository


class CreateBotUseCase:
    """Use case for creating a new bot."""
    
    def __init__(
        self,
        bot_repository: IBotRepository,
        strategy_repository: IStrategyRepository,
        exchange_repository: IExchangeRepository,
    ):
        self.bot_repository = bot_repository
        self.strategy_repository = strategy_repository
        self.exchange_repository = exchange_repository
    
    async def execute(
        self,
        user_id: UUID,
        name: str,
        strategy_id: UUID,
        exchange_connection_id: UUID,
        symbol: str,
        base_quantity: Decimal,
        quote_quantity: Decimal,
        max_active_orders: int,
        risk_percentage: Decimal,
        take_profit_percentage: Decimal,
        stop_loss_percentage: Decimal,
        description: Optional[str] = None,
        risk_level: RiskLevel = RiskLevel.MODERATE,
        max_daily_loss: Optional[Decimal] = None,
        max_drawdown: Optional[Decimal] = None,
        strategy_settings: Optional[dict] = None,
    ) -> Bot:
        """Create a new bot."""
        
        # Validate bot name uniqueness
        if await self.bot_repository.exists_by_name_and_user(name, user_id):
            raise DuplicateError(f"Bot with name '{name}' already exists")
        
        # Validate strategy exists and belongs to user
        strategy = await self.strategy_repository.find_by_id(strategy_id)
        if not strategy:
            raise NotFoundError(f"Strategy with id {strategy_id} not found")
        if strategy.user_id != user_id:
            raise ValidationError("Strategy does not belong to user")
        
        # Validate exchange connection
        exchange_connection = await self.exchange_repository.find_by_id(exchange_connection_id)
        if not exchange_connection:
            raise NotFoundError(f"Exchange connection with id {exchange_connection_id} not found")
        if exchange_connection.user_id != user_id:
            raise ValidationError("Exchange connection does not belong to user")
        
        # Create bot configuration
        configuration = BotConfiguration(
            symbol=symbol.upper(),
            base_quantity=base_quantity,
            quote_quantity=quote_quantity,
            max_active_orders=max_active_orders,
            risk_percentage=risk_percentage,
            take_profit_percentage=take_profit_percentage,
            stop_loss_percentage=stop_loss_percentage,
            strategy_settings=strategy_settings or {},
            max_daily_loss=max_daily_loss,
            max_drawdown=max_drawdown,
        )
        
        # Create bot entity
        bot = Bot.create(
            user_id=user_id,
            name=name,
            strategy_id=strategy_id,
            exchange_connection_id=exchange_connection_id,
            configuration=configuration,
            description=description,
            risk_level=risk_level,
        )
        
        # Save bot
        saved_bot = await self.bot_repository.save(bot)
        return saved_bot


class StartBotUseCase:
    """Use case for starting a bot."""
    
    def __init__(self, bot_repository: IBotRepository):
        self.bot_repository = bot_repository
    
    async def execute(self, user_id: UUID, bot_id: UUID) -> Bot:
        """Start a bot."""
        
        # Find bot
        bot = await self.bot_repository.find_by_id(bot_id)
        if not bot:
            raise NotFoundError(f"Bot with id {bot_id} not found")
        
        # Verify ownership
        if bot.user_id != user_id:
            raise ValidationError("Bot does not belong to user")
        
        # Verify can start
        if not bot.can_be_started():
            raise BusinessException(f"Cannot start bot in {bot.status} status")
        
        # Start bot
        bot.start()
        
        # Save updated bot
        updated_bot = await self.bot_repository.save(bot)
        return updated_bot


class StopBotUseCase:
    """Use case for stopping a bot."""
    
    def __init__(self, bot_repository: IBotRepository):
        self.bot_repository = bot_repository
    
    async def execute(self, user_id: UUID, bot_id: UUID, reason: Optional[str] = None) -> Bot:
        """Stop a bot."""
        
        # Find bot
        bot = await self.bot_repository.find_by_id(bot_id)
        if not bot:
            raise NotFoundError(f"Bot with id {bot_id} not found")
        
        # Verify ownership
        if bot.user_id != user_id:
            raise ValidationError("Bot does not belong to user")
        
        # Verify can stop
        if not bot.can_be_stopped():
            raise BusinessException(f"Cannot stop bot in {bot.status} status")
        
        # Stop bot
        bot.stop(reason=reason)
        
        # Save updated bot
        updated_bot = await self.bot_repository.save(bot)
        return updated_bot


class PauseBotUseCase:
    """Use case for pausing a bot."""
    
    def __init__(self, bot_repository: IBotRepository):
        self.bot_repository = bot_repository
    
    async def execute(self, user_id: UUID, bot_id: UUID, reason: Optional[str] = None) -> Bot:
        """Pause a bot."""
        
        # Find bot
        bot = await self.bot_repository.find_by_id(bot_id)
        if not bot:
            raise NotFoundError(f"Bot with id {bot_id} not found")
        
        # Verify ownership
        if bot.user_id != user_id:
            raise ValidationError("Bot does not belong to user")
        
        # Verify can pause
        if bot.status != BotStatus.ACTIVE:
            raise BusinessException(f"Cannot pause bot in {bot.status} status")
        
        # Pause bot
        bot.pause(reason=reason)
        
        # Save updated bot
        updated_bot = await self.bot_repository.save(bot)
        return updated_bot


class ResumeBotUseCase:
    """Use case for resuming a paused bot."""
    
    def __init__(self, bot_repository: IBotRepository):
        self.bot_repository = bot_repository
    
    async def execute(self, user_id: UUID, bot_id: UUID) -> Bot:
        """Resume a paused bot."""
        
        # Find bot
        bot = await self.bot_repository.find_by_id(bot_id)
        if not bot:
            raise NotFoundError(f"Bot with id {bot_id} not found")
        
        # Verify ownership
        if bot.user_id != user_id:
            raise ValidationError("Bot does not belong to user")
        
        # Verify can resume
        if bot.status != BotStatus.PAUSED:
            raise BusinessException(f"Cannot resume bot in {bot.status} status")
        
        # Resume bot
        bot.resume()
        
        # Save updated bot
        updated_bot = await self.bot_repository.save(bot)
        return updated_bot


class GetBotsUseCase:
    """Use case for retrieving user's bots."""
    
    def __init__(self, bot_repository: IBotRepository):
        self.bot_repository = bot_repository
    
    async def execute(self, user_id: UUID, status: Optional[BotStatus] = None) -> List[Bot]:
        """Get user's bots, optionally filtered by status."""
        
        if status:
            return await self.bot_repository.find_by_user_and_status(user_id, status)
        else:
            return await self.bot_repository.find_by_user(user_id)


class GetBotByIdUseCase:
    """Use case for retrieving a specific bot."""
    
    def __init__(self, bot_repository: IBotRepository):
        self.bot_repository = bot_repository
    
    async def execute(self, user_id: UUID, bot_id: UUID) -> Bot:
        """Get a specific bot by ID."""
        
        bot = await self.bot_repository.find_by_id(bot_id)
        if not bot:
            raise NotFoundError(f"Bot with id {bot_id} not found")
        
        # Verify ownership
        if bot.user_id != user_id:
            raise ValidationError("Bot does not belong to user")
        
        return bot


class UpdateBotConfigurationUseCase:
    """Use case for updating bot configuration."""
    
    def __init__(self, bot_repository: IBotRepository):
        self.bot_repository = bot_repository
    
    async def execute(
        self,
        user_id: UUID,
        bot_id: UUID,
        symbol: Optional[str] = None,
        base_quantity: Optional[Decimal] = None,
        quote_quantity: Optional[Decimal] = None,
        max_active_orders: Optional[int] = None,
        risk_percentage: Optional[Decimal] = None,
        take_profit_percentage: Optional[Decimal] = None,
        stop_loss_percentage: Optional[Decimal] = None,
        max_daily_loss: Optional[Decimal] = None,
        max_drawdown: Optional[Decimal] = None,
        strategy_settings: Optional[dict] = None,
    ) -> Bot:
        """Update bot configuration."""
        
        # Find bot
        bot = await self.bot_repository.find_by_id(bot_id)
        if not bot:
            raise NotFoundError(f"Bot with id {bot_id} not found")
        
        # Verify ownership
        if bot.user_id != user_id:
            raise ValidationError("Bot does not belong to user")
        
        # Verify bot is stopped
        if bot.status != BotStatus.STOPPED:
            raise BusinessException("Can only update configuration when bot is stopped")
        
        # Update configuration
        current_config = bot.configuration
        new_config = BotConfiguration(
            symbol=symbol or current_config.symbol,
            base_quantity=base_quantity or current_config.base_quantity,
            quote_quantity=quote_quantity or current_config.quote_quantity,
            max_active_orders=max_active_orders or current_config.max_active_orders,
            risk_percentage=risk_percentage or current_config.risk_percentage,
            take_profit_percentage=take_profit_percentage or current_config.take_profit_percentage,
            stop_loss_percentage=stop_loss_percentage or current_config.stop_loss_percentage,
            strategy_settings=strategy_settings or current_config.strategy_settings,
            max_daily_loss=max_daily_loss or current_config.max_daily_loss,
            max_drawdown=max_drawdown or current_config.max_drawdown,
        )
        
        bot.update_configuration(new_config)
        
        # Save updated bot
        updated_bot = await self.bot_repository.save(bot)
        return updated_bot


class DeleteBotUseCase:
    """Use case for deleting a bot."""
    
    def __init__(self, bot_repository: IBotRepository):
        self.bot_repository = bot_repository
    
    async def execute(self, user_id: UUID, bot_id: UUID) -> None:
        """Delete a bot."""
        
        # Find bot
        bot = await self.bot_repository.find_by_id(bot_id)
        if not bot:
            raise NotFoundError(f"Bot with id {bot_id} not found")
        
        # Verify ownership
        if bot.user_id != user_id:
            raise ValidationError("Bot does not belong to user")
        
        # Verify bot is stopped
        if bot.status != BotStatus.STOPPED:
            raise BusinessException("Can only delete stopped bots")
        
        # Delete bot
        await self.bot_repository.delete(bot_id)