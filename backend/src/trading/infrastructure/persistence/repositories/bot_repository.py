"""Bot and Strategy repository SQLAlchemy implementation."""
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
import logging
import uuid
from decimal import Decimal
from datetime import datetime

from ....domain.bot import (
    Bot, 
    Strategy,
    BotStatus, 
    StrategyType,
    RiskLevel,
    BotConfiguration, 
    BotPerformance,
    StrategyParameters,
    BotType,
)
from ....domain.bot.repository import IBotRepository, IStrategyRepository
from ..models.bot_models import BotModel, StrategyModel


class BotRepository(IBotRepository):
    """SQLAlchemy implementation of bot repository."""
    
    def __init__(self, session: AsyncSession):
        self._session = session
    
    def _model_to_domain(self, model: BotModel) -> Bot:
        """Convert database model to domain entity."""
        # Parse configuration
        config_data = model.configuration
        configuration = BotConfiguration(
            symbol=config_data["symbol"],
            base_quantity=Decimal(str(config_data["base_quantity"])),
            quote_quantity=Decimal(str(config_data["quote_quantity"])),
            max_active_orders=config_data["max_active_orders"],
            risk_percentage=Decimal(str(config_data["risk_percentage"])),
            take_profit_percentage=Decimal(str(config_data["take_profit_percentage"])),
            stop_loss_percentage=Decimal(str(config_data["stop_loss_percentage"])),
            strategy_settings=config_data.get("strategy_settings", {}),
            max_daily_loss=Decimal(str(config_data["max_daily_loss"])) if config_data.get("max_daily_loss") else None,
            max_drawdown=Decimal(str(config_data["max_drawdown"])) if config_data.get("max_drawdown") else None,
            bot_type=BotType(config_data["bot_type"]) if config_data.get("bot_type") else None,
        )
        
        # Parse performance (legacy JSON column mixed with new columns)
        perf_data = model.performance or {}
        performance = BotPerformance(
            total_trades=model.total_trades if model.total_trades else perf_data.get("total_trades", 0),
            winning_trades=model.winning_trades if model.winning_trades else perf_data.get("winning_trades", 0),
            losing_trades=model.losing_trades if model.losing_trades else perf_data.get("losing_trades", 0),
            total_profit_loss=model.total_pnl if model.total_pnl is not None else Decimal(str(perf_data.get("total_profit_loss", "0"))),
            total_fees=Decimal(str(perf_data.get("total_fees", "0"))),
            max_drawdown=Decimal(str(perf_data.get("max_drawdown", "0"))),
            sharpe_ratio=Decimal(str(perf_data["sharpe_ratio"])) if perf_data.get("sharpe_ratio") else None,
        )
        
        # Create Bot domain entity
        return Bot(
            id=model.id,
            user_id=model.user_id,
            name=model.name,
            strategy_id=model.strategy_id,
            exchange_connection_id=model.exchange_connection_id,
            status=BotStatus(model.status),
            configuration=configuration,
            created_at=datetime.fromisoformat(str(model.created_at)) if isinstance(model.created_at, str) else model.created_at,
            updated_at=datetime.fromisoformat(str(model.updated_at)) if isinstance(model.updated_at, str) else model.updated_at,
            description=model.description,
            risk_level=RiskLevel(model.risk_level),
            start_time=datetime.fromisoformat(str(model.start_time)) if isinstance(model.start_time, str) else model.start_time,
            stop_time=datetime.fromisoformat(str(model.stop_time)) if isinstance(model.stop_time, str) else model.stop_time,
            last_error=model.last_error,
            performance=performance,
            active_orders=model.active_orders,
            daily_pnl=model.daily_pnl,
            total_runtime_seconds=model.total_runtime_seconds,
            metadata=model.meta_data,
            # NEW: Map cumulative stats from DB columns
            total_pnl=model.total_pnl or Decimal("0"),
            total_trades=model.total_trades or 0,
            winning_trades=model.winning_trades or 0,
            losing_trades=model.losing_trades or 0,
            # NEW: Map streak fields from DB columns
            current_win_streak=model.current_win_streak or 0,
            current_loss_streak=model.current_loss_streak or 0,
            max_win_streak=model.max_win_streak or 0,
            max_loss_streak=model.max_loss_streak or 0,
        )
    
    def _domain_to_model_data(self, bot: Bot) -> dict:
        """Convert domain entity to model data."""
        return {
            "id": bot.id,
            "user_id": bot.user_id,
            "name": bot.name,
            "description": bot.description,
            "strategy_id": bot.strategy_id,
            "exchange_connection_id": bot.exchange_connection_id,
            "status": bot.status.value,
            "risk_level": bot.risk_level.value,
            "configuration": {
                "symbol": bot.configuration.symbol,
                "base_quantity": str(bot.configuration.base_quantity),
                "quote_quantity": str(bot.configuration.quote_quantity),
                "max_active_orders": bot.configuration.max_active_orders,
                "risk_percentage": str(bot.configuration.risk_percentage),
                "take_profit_percentage": str(bot.configuration.take_profit_percentage),
                "stop_loss_percentage": str(bot.configuration.stop_loss_percentage),
                "strategy_settings": bot.configuration.strategy_settings,
                "max_daily_loss": str(bot.configuration.max_daily_loss) if bot.configuration.max_daily_loss else None,
                "max_drawdown": str(bot.configuration.max_drawdown) if bot.configuration.max_drawdown else None,
                "bot_type": bot.configuration.bot_type.value if bot.configuration.bot_type else None,
            },
            "start_time": bot.start_time,
            "stop_time": bot.stop_time,
            "last_error": bot.last_error,
            "performance": {
                "total_trades": bot.performance.total_trades,
                "winning_trades": bot.performance.winning_trades,
                "losing_trades": bot.performance.losing_trades,
                "total_profit_loss": str(bot.performance.total_profit_loss),
                "total_fees": str(bot.performance.total_fees),
                "max_drawdown": str(bot.performance.max_drawdown),
                "sharpe_ratio": str(bot.performance.sharpe_ratio) if bot.performance.sharpe_ratio else None,
            },
            "active_orders": bot.active_orders,
            "daily_pnl": bot.daily_pnl,
            "total_runtime_seconds": bot.total_runtime_seconds,
            "meta_data": bot.metadata,
            "created_at": bot.created_at,
            "updated_at": bot.updated_at,
        }

    async def save(self, bot: Bot) -> Bot:
        """Save or update bot."""
        stmt = select(BotModel).where(BotModel.id == bot.id)
        result = await self._session.execute(stmt)
        existing = result.scalar_one_or_none()
        
        data = self._domain_to_model_data(bot)
        
        if existing:
            # Update existing
            for key, value in data.items():
                if key not in ['id', 'created_at']:  # Don't update immutable fields
                    setattr(existing, key, value)
        else:
            # Create new
            existing = BotModel(**data)
            self._session.add(existing)
        
        await self._session.commit()
        await self._session.refresh(existing)
        
        return self._model_to_domain(existing)
    
    async def find_by_id(self, bot_id: uuid.UUID) -> Optional[Bot]:
        """Find bot by ID."""
        stmt = select(BotModel).where(
            and_(BotModel.id == bot_id, BotModel.deleted_at.is_(None))
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        
        if model:
            return self._model_to_domain(model)
        return None
    
    async def find_by_user(self, user_id: uuid.UUID) -> List[Bot]:
        """Find all bots for a user."""
        stmt = select(BotModel).where(
            and_(BotModel.user_id == user_id, BotModel.deleted_at.is_(None))
        ).order_by(BotModel.created_at.desc())
        
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        
        return [self._model_to_domain(model) for model in models]
    
    async def find_by_user_and_status(self, user_id: uuid.UUID, status: BotStatus) -> List[Bot]:
        """Find bots by user ID and status."""
        stmt = select(BotModel).where(
            and_(
                BotModel.user_id == user_id,
                BotModel.status == status.value,
                BotModel.deleted_at.is_(None)
            )
        ).order_by(BotModel.created_at.desc())
        
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        
        return [self._model_to_domain(model) for model in models]
    
    async def find_by_strategy_id(self, strategy_id: uuid.UUID) -> List[Bot]:
        """Find bots using specific strategy."""
        stmt = select(BotModel).where(
            and_(
                BotModel.strategy_id == strategy_id,
                BotModel.deleted_at.is_(None)
            )
        ).order_by(BotModel.created_at.desc())
        
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        
        return [self._model_to_domain(model) for model in models]
    
    async def find_active_bots(self) -> List[Bot]:
        """Find all active bots across all users."""
        stmt = select(BotModel).where(
            and_(
                BotModel.status == BotStatus.RUNNING.value,
                BotModel.deleted_at.is_(None)
            )
        ).order_by(BotModel.updated_at.desc())
        
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        
        return [self._model_to_domain(model) for model in models]
    
    async def exists_by_name_and_user(self, name: str, user_id: uuid.UUID) -> bool:
        """Check if bot with name exists for user."""
        stmt = select(BotModel.id).where(
            and_(
                BotModel.name == name,
                BotModel.user_id == user_id,
                BotModel.deleted_at.is_(None)
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None
    
    async def delete(self, bot_id: uuid.UUID) -> None:
        """Delete bot (soft delete)."""
        stmt = select(BotModel).where(BotModel.id == bot_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        
        if model:
            from datetime import datetime, timezone
            model.deleted_at = datetime.now(timezone.utc)
            await self._session.commit()


class StrategyRepository(IStrategyRepository):
    """SQLAlchemy implementation of strategy repository."""
    
    def __init__(self, session: AsyncSession):
        self._session = session
    
    def _model_to_domain(self, model: StrategyModel) -> Strategy:
        """Convert database model to domain entity."""
        # Parse parameters - parameters column contains only strategy-specific params
        # NOT name/description (those are separate columns in the table)
        params_data = model.parameters or {}
        parameters = StrategyParameters(
            strategy_type=StrategyType(model.strategy_type),
            name=model.name,  # ✅ FIX: Use model.name column
            description=model.description or "",  # ✅ FIX: Use model.description column
            parameters=params_data  # ✅ FIX: Use entire params_data dict
        )
        
        # Parse performance
        perf_data = model.live_performance or {}
        live_performance = BotPerformance(
            total_trades=perf_data.get("total_trades", 0),
            winning_trades=perf_data.get("winning_trades", 0),
            losing_trades=perf_data.get("losing_trades", 0),
            total_profit_loss=Decimal(str(perf_data.get("total_profit_loss", "0"))),
            total_fees=Decimal(str(perf_data.get("total_fees", "0"))),
            max_drawdown=Decimal(str(perf_data.get("max_drawdown", "0"))),
            sharpe_ratio=Decimal(str(perf_data["sharpe_ratio"])) if perf_data.get("sharpe_ratio") else None,
        )
        
        # Create Strategy domain entity
        return Strategy(
            id=model.id,
            user_id=model.user_id,
            name=model.name,
            strategy_type=StrategyType(model.strategy_type),
            description=model.description,
            parameters=parameters,
            is_active=model.is_active,
            created_at=model.created_at,
            updated_at=model.updated_at,
            backtest_results=model.backtest_results,
            live_performance=live_performance,
        )
    
    def _domain_to_model_data(self, strategy: Strategy) -> dict:
        """Convert domain entity to model data."""
        return {
            "id": strategy.id,
            "user_id": strategy.user_id,
            "name": strategy.name,
            "strategy_type": strategy.strategy_type.value,
            "description": strategy.description,
            "parameters": {
                "name": strategy.parameters.name,
                "description": strategy.parameters.description,
                "parameters": strategy.parameters.parameters,
            },
            "is_active": strategy.is_active,
            "created_at": strategy.created_at,
            "updated_at": strategy.updated_at,
            "backtest_results": strategy.backtest_results,
            "live_performance": {
                "total_trades": strategy.live_performance.total_trades,
                "winning_trades": strategy.live_performance.winning_trades,
                "losing_trades": strategy.live_performance.losing_trades,
                "total_profit_loss": str(strategy.live_performance.total_profit_loss),
                "total_fees": str(strategy.live_performance.total_fees),
                "max_drawdown": str(strategy.live_performance.max_drawdown),
                "sharpe_ratio": str(strategy.live_performance.sharpe_ratio) if strategy.live_performance.sharpe_ratio else None,
            },
        }

    async def save(self, strategy: Strategy) -> Strategy:
        """Save or update strategy."""
        stmt = select(StrategyModel).where(StrategyModel.id == strategy.id)
        result = await self._session.execute(stmt)
        existing = result.scalar_one_or_none()
        
        data = self._domain_to_model_data(strategy)
        
        if existing:
            # Update existing
            for key, value in data.items():
                if key not in ['id', 'created_at']:  # Don't update immutable fields
                    setattr(existing, key, value)
        else:
            # Create new
            existing = StrategyModel(**data)
            self._session.add(existing)
        
        await self._session.commit()
        await self._session.refresh(existing)
        
        return self._model_to_domain(existing)
    
    async def find_by_id(self, strategy_id: uuid.UUID) -> Optional[Strategy]:
        """Find strategy by ID."""
        print(f"\n\n=== STRATEGY REPOSITORY find_by_id CALLED ===")
        print(f"=== Strategy ID: {strategy_id} ===")
        print(f"=== Session: {self._session} ===\n")
        logger = logging.getLogger(__name__)
        stmt = select(StrategyModel).where(
            and_(StrategyModel.id == strategy_id, StrategyModel.deleted_at.is_(None))
        )
        print(f"DEBUG: StrategyRepository.find_by_id: {strategy_id}")
        print(f"DEBUG: SQL: {stmt}")
        
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        print(f"DEBUG: StrategyRepository found model: {model}")
        
        if model:
            print(f"DEBUG: Model found! ID={model.id}, name={model.name}, type={model.strategy_type}")
            print(f"DEBUG: Parameters: {model.parameters}")
            print(f"DEBUG: Live Performance: {model.live_performance}")
            try:
                domain = self._model_to_domain(model)
                print(f"DEBUG: Successfully converted to domain: {domain.name}")
                return domain
            except Exception as e:
                print(f"ERROR: Failed to convert model to domain: {e}")
                logger.error(f"Failed to convert strategy model to domain: {e}", exc_info=True)
                return None
        return None
    
    async def find_by_user(self, user_id: uuid.UUID) -> List[Strategy]:
        """Find all strategies for a user."""
        stmt = select(StrategyModel).where(
            and_(StrategyModel.user_id == user_id, StrategyModel.deleted_at.is_(None))
        ).order_by(StrategyModel.created_at.desc())
        
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        
        return [self._model_to_domain(model) for model in models]
    
    async def find_by_type(self, strategy_type: StrategyType) -> List[Strategy]:
        """Find strategies by type."""
        stmt = select(StrategyModel).where(
            and_(
                StrategyModel.strategy_type == strategy_type.value,
                StrategyModel.deleted_at.is_(None)
            )
        ).order_by(StrategyModel.created_at.desc())
        
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        
        return [self._model_to_domain(model) for model in models]
    
    async def find_active_strategies(self) -> List[Strategy]:
        """Find all active strategies."""
        stmt = select(StrategyModel).where(
            and_(
                StrategyModel.is_active == True,
                StrategyModel.deleted_at.is_(None)
            )
        ).order_by(StrategyModel.updated_at.desc())
        
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        
        return [self._model_to_domain(model) for model in models]
    
    async def exists_by_name_and_user(self, name: str, user_id: uuid.UUID) -> bool:
        """Check if strategy with name exists for user."""
        stmt = select(StrategyModel.id).where(
            and_(
                StrategyModel.name == name,
                StrategyModel.user_id == user_id,
                StrategyModel.deleted_at.is_(None)
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None
    
    async def delete(self, strategy_id: uuid.UUID) -> None:
        """Delete strategy (soft delete)."""
        stmt = select(StrategyModel).where(StrategyModel.id == strategy_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        
        if model:
            from datetime import datetime, timezone
            model.deleted_at = datetime.now(timezone.utc)
            await self._session.commit()


__all__ = ["BotRepository", "StrategyRepository"]
