"""Seed exchange data."""
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models.core_models import ExchangeModel

logger = logging.getLogger(__name__)


async def seed_exchanges(session: AsyncSession) -> None:
    """Seed supported exchanges if they don't exist."""
    exchanges = [
        {
            "code": "BINANCE",
            "name": "Binance",
            "api_base_url": "https://api.binance.com",
            "supported_features": {
                "spot": True,
                "futures": True,
                "margin": True,
                "testnet": True
            },
            "rate_limits": {
                "requests_per_minute": 1200,
                "orders_per_second": 10
            }
        },
        {
            "code": "BYBIT",
            "name": "Bybit",
            "api_base_url": "https://api.bybit.com",
            "supported_features": {
                "spot": True,
                "futures": True,
                "margin": True,
                "testnet": True
            },
            "rate_limits": {
                "requests_per_minute": 600,
                "orders_per_second": 10
            }
        },
        {
            "code": "OKX",
            "name": "OKX",
            "api_base_url": "https://www.okx.com",
            "supported_features": {
                "spot": True,
                "futures": True,
                "margin": True,
                "testnet": True
            },
            "rate_limits": {
                "requests_per_minute": 600,
                "orders_per_second": 10
            }
        }
    ]

    try:
        for exchange_data in exchanges:
            # Check if exists
            stmt = select(ExchangeModel).where(ExchangeModel.code == exchange_data["code"])
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()

            if not existing:
                logger.info(f"Seeding exchange: {exchange_data['name']}")
                exchange = ExchangeModel(**exchange_data)
                session.add(exchange)
            else:
                logger.debug(f"Exchange already exists: {exchange_data['name']}")
        
        await session.commit()
        
    except Exception as e:
        logger.error(f"Failed to seed exchanges: {e}")
        await session.rollback()
        raise
