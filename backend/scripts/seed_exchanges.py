"""Seed exchanges table with initial data."""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from trading.infrastructure.persistence.models.core_models import ExchangeModel
from trading.infrastructure.config.settings import get_settings


async def seed_exchanges():
    """Seed exchanges table with BINANCE, BYBIT, OKX."""
    settings = get_settings()
    
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=True
    )
    
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    exchanges = [
        {
            "code": "BINANCE",
            "name": "Binance Futures",
            "api_base_url": "https://fapi.binance.com",
            "is_active": True
        },
        {
            "code": "BYBIT",
            "name": "Bybit",
            "api_base_url": "https://api.bybit.com",
            "is_active": True
        },
        {
            "code": "OKX",
            "name": "OKX",
            "api_base_url": "https://www.okx.com",
            "is_active": True
        }
    ]
    
    async with async_session() as session:
        # Check if exchanges already exist
        for exchange_data in exchanges:
            result = await session.execute(
                select(ExchangeModel).where(ExchangeModel.code == exchange_data["code"])
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                print(f"✓ Exchange {exchange_data['code']} already exists")
            else:
                exchange = ExchangeModel(**exchange_data)
                session.add(exchange)
                print(f"+ Adding exchange {exchange_data['code']}")
        
        await session.commit()
        print("\n✓ Exchanges seeded successfully")


if __name__ == "__main__":
    asyncio.run(seed_exchanges())
