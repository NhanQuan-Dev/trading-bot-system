"""Script to create test database tables directly."""

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from src.trading.infrastructure.persistence.database import Base

# Import models to register them with Base metadata
from src.trading.infrastructure.persistence.models import (
    UserModel, ExchangeModel, APIConnectionModel, DatabaseConfigModel, SymbolModel,
    OrderModel, PositionModel, TradeModel,
    BotModel, StrategyModel, BacktestModel, BotPerformanceModel,
    MarketPriceModel, OrderBookSnapshotModel,
    RiskLimitModel, AlertModel, EventQueueModel
)

async def create_tables():
    """Create all tables in the test database."""
    engine = create_async_engine(
        "postgresql+asyncpg://test_user:test_password@localhost:5433/trading_test"
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    await engine.dispose()
    print("Tables created successfully!")

if __name__ == "__main__":
    asyncio.run(create_tables())