"""Seed initial strategies."""
import logging
import uuid
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from .models.bot_models import StrategyModel

logger = logging.getLogger(__name__)

# Strategy IDs matching frontend configuration
STRATEGIES = [
    {
        "id": uuid.UUID("00000000-0000-0000-0000-000000000001"),
        "name": "Grid Trading",
        "strategy_type": "GRID",
        "description": "Grid trading strategy for range-bound markets",
        "parameters": {"grid_levels": 10, "grid_step": 1.0}
    },
    {
        "id": uuid.UUID("00000000-0000-0000-0000-000000000002"),
        "name": "Momentum Strategy",
        "strategy_type": "TREND_FOLLOWING",
        "description": "Trend following momentum strategy",
        "parameters": {"period": 14, "threshold": 2.0}
    },
    {
        "id": uuid.UUID("00000000-0000-0000-0000-000000000003"),
        "name": "Mean Reversion",
        "strategy_type": "MEAN_REVERSION",
        "description": "Mean reversion strategy using Bollinger Bands",
        "parameters": {"period": 20, "std_dev": 2.0}
    },
    {
        "id": uuid.UUID("00000000-0000-0000-0000-000000000004"),
        "name": "Arbitrage",
        "strategy_type": "ARBITRAGE",
        "description": "Spatial arbitrage strategy",
        "parameters": {"min_spread": 0.5}
    },
    {
        "id": uuid.UUID("00000000-0000-0000-0000-000000000005"),
        "name": "Scalping",
        "strategy_type": "CUSTOM",
        "description": "High frequency scalping strategy",
        "parameters": {"take_profit": 0.5, "stop_loss": 0.2}
    }
]

DEFAULT_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")

async def seed_strategies(session: AsyncSession):
    """Seed initial strategies."""
    try:
        for strat_data in STRATEGIES:
            # Check if strategy exists
            stmt = select(StrategyModel).where(StrategyModel.id == strat_data["id"])
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()
            
            if not existing:
                logger.info(f"Seeding strategy: {strat_data['name']}")
                strategy = StrategyModel(
                    id=strat_data["id"],
                    user_id=DEFAULT_USER_ID,
                    name=strat_data["name"],
                    strategy_type=strat_data["strategy_type"],
                    description=strat_data["description"],
                    parameters=strat_data["parameters"]
                )
                session.add(strategy)
            else:
                # Update name if it doesn't match (fixing "Default Strategy" issue)
                if existing.name != strat_data["name"]:
                    logger.info(f"Updating strategy name: {existing.name} -> {strat_data['name']}")
                    existing.name = strat_data["name"]
                    existing.description = strat_data["description"]
                    existing.strategy_type = strat_data["strategy_type"]
                    session.add(existing)
                    
        await session.commit()
            
    except Exception as e:
        logger.error(f"Error seeding strategies: {e}")
        # Don't raise here to allow app startup to continue even if seeding fails
