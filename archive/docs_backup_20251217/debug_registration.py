"""Debug script to test registration endpoint manually."""
import asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool
from sqlalchemy import text
import os

from src.trading.infrastructure.persistence.database import Base, get_db

# Import all models to ensure they're registered
from src.trading.infrastructure.persistence.models import (
    core_models, bot_models, trading_models, market_data_models,
    risk_models, backtest_models
)

async def test_registration():
    # Database setup
    TEST_DATABASE_URL = "postgresql+asyncpg://test_user:test_password@localhost:5433/trading_test"
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool, echo=False)
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    # Create app
    from src.trading.app import create_app
    app = create_app()
    
    # Override database dependency
    async def override_get_db():
        async with async_session() as session:
            yield session
    
    app.dependency_overrides[get_db] = override_get_db
    
    # Test registration
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "password": "SecurePass123!",
                "full_name": "Test User"
            }
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        print(f"Response: {response.text}")
        
        if response.status_code != 201:
            print(f"Expected 201, got {response.status_code}")
        else:
            data = response.json()
            print(f"Success! Email: {data.get('email', 'NOT FOUND')}")
    
    # Cleanup
    async with engine.begin() as conn:
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(test_registration())