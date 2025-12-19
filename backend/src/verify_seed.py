import asyncio
from sqlalchemy import select
from trading.infrastructure.persistence.database import get_db_context
from trading.infrastructure.persistence.models.core_models import ExchangeModel

async def check_exchanges():
    async with get_db_context() as session:
        stmt = select(ExchangeModel)
        result = await session.execute(stmt)
        exchanges = result.scalars().all()
        
        print(f"Found {len(exchanges)} exchanges:")
        for exchange in exchanges:
            print(f"- {exchange.code}: {exchange.name} (Active: {exchange.is_active})")

if __name__ == "__main__":
    asyncio.run(check_exchanges())
