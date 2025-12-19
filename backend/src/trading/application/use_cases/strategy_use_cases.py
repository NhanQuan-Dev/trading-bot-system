"""Strategy use cases."""
from typing import Optional, List, Dict, Any
from uuid import UUID

from ...shared.exceptions import (
    NotFoundError, 
    ValidationError, 
    DuplicateError
)
from ...domain.bot import Strategy, StrategyType
from ...domain.bot.repository import IStrategyRepository, IBotRepository


class CreateStrategyUseCase:
    """Use case for creating a new strategy."""
    
    def __init__(self, strategy_repository: IStrategyRepository):
        self.strategy_repository = strategy_repository
    
    async def execute(
        self,
        user_id: UUID,
        name: str,
        strategy_type: StrategyType,
        description: str,
        parameters: Dict[str, Any],
    ) -> Strategy:
        """Create a new strategy."""
        
        # Validate strategy name uniqueness
        if await self.strategy_repository.exists_by_name_and_user(name, user_id):
            raise DuplicateError(f"Strategy with name '{name}' already exists")
        
        # Create strategy
        strategy = Strategy.create(
            user_id=user_id,
            name=name,
            strategy_type=strategy_type,
            description=description,
            parameters=parameters,
        )
        
        # Save strategy
        saved_strategy = await self.strategy_repository.save(strategy)
        return saved_strategy


class GetStrategiesUseCase:
    """Use case for retrieving user's strategies."""
    
    def __init__(self, strategy_repository: IStrategyRepository):
        self.strategy_repository = strategy_repository
    
    async def execute(
        self, 
        user_id: UUID, 
        strategy_type: Optional[StrategyType] = None
    ) -> List[Strategy]:
        """Get user's strategies, optionally filtered by type."""
        
        if strategy_type:
            # Get all strategies of type, then filter by user
            all_strategies = await self.strategy_repository.find_by_type(strategy_type)
            return [s for s in all_strategies if s.user_id == user_id]
        else:
            return await self.strategy_repository.find_by_user(user_id)


class GetStrategyByIdUseCase:
    """Use case for retrieving a specific strategy."""
    
    def __init__(self, strategy_repository: IStrategyRepository):
        self.strategy_repository = strategy_repository
    
    async def execute(self, user_id: UUID, strategy_id: UUID) -> Strategy:
        """Get a specific strategy by ID."""
        
        strategy = await self.strategy_repository.find_by_id(strategy_id)
        if not strategy:
            raise NotFoundError(f"Strategy with id {strategy_id} not found")
        
        # Verify ownership
        if strategy.user_id != user_id:
            raise ValidationError("Strategy does not belong to user")
        
        return strategy


class UpdateStrategyUseCase:
    """Use case for updating a strategy."""
    
    def __init__(self, strategy_repository: IStrategyRepository):
        self.strategy_repository = strategy_repository
    
    async def execute(
        self,
        user_id: UUID,
        strategy_id: UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Strategy:
        """Update a strategy."""
        
        # Find strategy
        strategy = await self.strategy_repository.find_by_id(strategy_id)
        if not strategy:
            raise NotFoundError(f"Strategy with id {strategy_id} not found")
        
        # Verify ownership
        if strategy.user_id != user_id:
            raise ValidationError("Strategy does not belong to user")
        
        # Check name uniqueness if name is being changed
        if name and name != strategy.name:
            if await self.strategy_repository.exists_by_name_and_user(name, user_id):
                raise DuplicateError(f"Strategy with name '{name}' already exists")
            strategy.name = name
        
        # Update description if provided
        if description is not None:
            strategy.description = description
        
        # Update parameters if provided
        if parameters is not None:
            strategy.update_parameters(parameters)
        
        # Save updated strategy
        updated_strategy = await self.strategy_repository.save(strategy)
        return updated_strategy


class ActivateStrategyUseCase:
    """Use case for activating a strategy."""
    
    def __init__(self, strategy_repository: IStrategyRepository):
        self.strategy_repository = strategy_repository
    
    async def execute(self, user_id: UUID, strategy_id: UUID) -> Strategy:
        """Activate a strategy."""
        
        # Find strategy
        strategy = await self.strategy_repository.find_by_id(strategy_id)
        if not strategy:
            raise NotFoundError(f"Strategy with id {strategy_id} not found")
        
        # Verify ownership
        if strategy.user_id != user_id:
            raise ValidationError("Strategy does not belong to user")
        
        # Activate strategy
        strategy.activate()
        
        # Save updated strategy
        updated_strategy = await self.strategy_repository.save(strategy)
        return updated_strategy


class DeactivateStrategyUseCase:
    """Use case for deactivating a strategy."""
    
    def __init__(
        self, 
        strategy_repository: IStrategyRepository,
        bot_repository: IBotRepository
    ):
        self.strategy_repository = strategy_repository
        self.bot_repository = bot_repository
    
    async def execute(self, user_id: UUID, strategy_id: UUID) -> Strategy:
        """Deactivate a strategy."""
        
        # Find strategy
        strategy = await self.strategy_repository.find_by_id(strategy_id)
        if not strategy:
            raise NotFoundError(f"Strategy with id {strategy_id} not found")
        
        # Verify ownership
        if strategy.user_id != user_id:
            raise ValidationError("Strategy does not belong to user")
        
        # Check if any active bots are using this strategy
        bots_using_strategy = await self.bot_repository.find_by_strategy_id(strategy_id)
        active_bots = [bot for bot in bots_using_strategy if bot.is_active()]
        
        if active_bots:
            bot_names = [bot.name for bot in active_bots]
            raise ValidationError(
                f"Cannot deactivate strategy. Active bots using this strategy: {', '.join(bot_names)}"
            )
        
        # Deactivate strategy
        strategy.deactivate()
        
        # Save updated strategy
        updated_strategy = await self.strategy_repository.save(strategy)
        return updated_strategy


class DeleteStrategyUseCase:
    """Use case for deleting a strategy."""
    
    def __init__(
        self, 
        strategy_repository: IStrategyRepository,
        bot_repository: IBotRepository
    ):
        self.strategy_repository = strategy_repository
        self.bot_repository = bot_repository
    
    async def execute(self, user_id: UUID, strategy_id: UUID) -> None:
        """Delete a strategy."""
        
        # Find strategy
        strategy = await self.strategy_repository.find_by_id(strategy_id)
        if not strategy:
            raise NotFoundError(f"Strategy with id {strategy_id} not found")
        
        # Verify ownership
        if strategy.user_id != user_id:
            raise ValidationError("Strategy does not belong to user")
        
        # Check if any bots are using this strategy
        bots_using_strategy = await self.bot_repository.find_by_strategy_id(strategy_id)
        
        if bots_using_strategy:
            bot_names = [bot.name for bot in bots_using_strategy]
            raise ValidationError(
                f"Cannot delete strategy. Bots using this strategy: {', '.join(bot_names)}"
            )
        
        # Delete strategy
        await self.strategy_repository.delete(strategy_id)