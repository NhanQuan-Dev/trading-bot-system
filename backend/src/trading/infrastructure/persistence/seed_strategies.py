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
    },
    {
        "id": uuid.UUID("00000000-0000-0000-0000-000000000006"),
        "name": "HighFrequencyTest",
        "strategy_type": "CUSTOM",
        "description": "Test strategy that alternates BUY/SELL every few ticks to generate maximum trades quickly. FOR TESTING ONLY!",
        "parameters": {"tick_interval": 2, "quantity": "0.001", "use_market_orders": True, "max_position": "0.01"}
    },
    {
        "id": uuid.UUID("00000000-0000-0000-0000-000000000007"),
        "name": "Martingale Smart MTF (Fixed SL)",
        "strategy_type": "MARTINGALE",
        "description": "Martingale strategy with Multi-Timeframe trend filter (4h) and fixed Stop Loss.",
        "parameters": {
            "initial_capital": 10000,
            "base_order_size": 100,
            "safety_order_size": 100,
            "max_safety_orders": 5,
            "price_deviation": 1.0,
            "volume_scale": 2.0,
            "safety_order_step_scale": 1.5,
            "take_profit": 1.5,
            "stop_loss": 10.0,
            "trend_timeframe": "4h",
            "trend_ma_period": 20
        },
        "code_content": """
from src.trading.strategies.base import StrategyBase
import pandas as pd
import numpy as np

class MartingaleSmartMTF(StrategyBase):
    name = "Martingale Smart MTF (Fixed SL)"
    
    def __init__(self, exchange, config):
        super().__init__(exchange, config)
        self.required_timeframes = ["1h", "4h"]  # REQUIRED for UI Detection
        self.params = config.get("parameters", {})
        
    async def on_tick(self, market_data):
        # Implementation placeholder
        pass
"""
    }
]

DEFAULT_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")

async def seed_strategies(session: AsyncSession):
    """Seed initial strategies."""
    try:
        for strat_data in STRATEGIES:
            # Check if strategy exists
            # Check if strategy exists by ID
            stmt = select(StrategyModel).where(StrategyModel.id == strat_data["id"])
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()

            # If not found by ID, check by Name (to avoid unique constraint violations on insert)
            if not existing:
                from sqlalchemy import and_
                stmt_name = select(StrategyModel).where(
                    and_(
                        StrategyModel.name == strat_data["name"],
                        StrategyModel.user_id == DEFAULT_USER_ID,
                        StrategyModel.deleted_at.is_(None) # Only check active ones
                    )
                )
                result_name = await session.execute(stmt_name)
                existing = result_name.scalar_one_or_none()
                
                if existing:
                    logger.info(f"Found existing strategy by name: {strat_data['name']} (ID: {existing.id})")
            
            if not existing:
                logger.info(f"Seeding strategy: {strat_data['name']}")
                strategy = StrategyModel(
                    id=strat_data["id"],
                    user_id=DEFAULT_USER_ID,
                    name=strat_data["name"],
                    strategy_type=strat_data["strategy_type"],
                    description=strat_data["description"],
                    parameters=strat_data["parameters"],
                    code_content=strat_data.get("code_content")
                )
                session.add(strategy)
            else:
                # Update name if it doesn't match (fixing "Default Strategy" issue)
                if existing.name != strat_data["name"]:
                    logger.info(f"Updating strategy name: {existing.name} -> {strat_data['name']}")
                    existing.name = strat_data["name"]
                    existing.description = strat_data["description"]
                    existing.strategy_type = strat_data["strategy_type"]
                
                # Always update code_content if present (to ensure updates are propagated)
                if "code_content" in strat_data:
                    existing.code_content = strat_data["code_content"]
                
                session.add(existing)
                    
        await session.commit()
            
    except Exception as e:
        logger.error(f"Error seeding strategies: {e}")
        # Don't raise here to allow app startup to continue even if seeding fails
