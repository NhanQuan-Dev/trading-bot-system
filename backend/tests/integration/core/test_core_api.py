"""
API Integration Test Framework
Tests all FastAPI endpoints with proper database fixtures and authentication.
"""
import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool
from sqlalchemy import text
from datetime import datetime, timezone
from typing import AsyncGenerator, Dict

from src.trading.infrastructure.persistence.database import Base, get_db
from src.trading.infrastructure.config.settings import Settings
from src.trading.infrastructure.auth.jwt import create_access_token
from src.trading.infrastructure.persistence.models.core_models import UserModel
from src.trading.domain.user import HashedPassword
import uuid
import os

# Import all models to ensure they're registered with Base.metadata
from src.trading.infrastructure.persistence.models import (
    core_models, bot_models, trading_models, market_data_models,
    risk_models, backtest_models
)


# Test database URL (PostgreSQL for realistic testing with JSONB, ARRAY, UUID support)
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://test_user:test_password@localhost:5433/trading_test"
)


@pytest.fixture(scope="function")
async def test_db_engine():
    """Create a test database engine with PostgreSQL."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=NullPool,
        echo=False
    )
    
    # Create all tables for comprehensive testing
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Cleanup - drop all tables with CASCADE to handle circular dependencies
    async with engine.begin() as conn:
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
        await conn.commit()
    
    await engine.dispose()


@pytest.fixture(scope="function")
async def test_db_session(test_db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    async_session = async_sessionmaker(
        test_db_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session


@pytest.fixture(scope="function")
async def test_app(test_db_session):
    """Create a FastAPI test app with test database."""
    from src.trading.app import create_app
    
    app = create_app()
    
    # Override database dependency
    async def override_get_db():
        yield test_db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    yield app
    
    # Cleanup
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
async def client(test_app) -> AsyncGenerator[AsyncClient, None]:
    """Create an async HTTP client for testing."""
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture(scope="function")
async def test_user(test_db_session) -> Dict:
    """Create a test user in the database."""
    user_id = uuid.uuid4()
    hashed_password = HashedPassword.from_plain("TestPassword123!")
    
    user = UserModel(
        id=user_id,
        email="test@example.com",
        password_hash=hashed_password.value,
        full_name="Test User",
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    
    test_db_session.add(user)
    await test_db_session.commit()
    await test_db_session.refresh(user)
    
    return {
        "id": str(user.id),
        "email": user.email,
        "password": "TestPassword123!",
        "full_name": user.full_name
    }


@pytest.fixture(scope="function")
def auth_headers(test_user) -> Dict[str, str]:
    """Create authentication headers with JWT token."""
    token = create_access_token(user_id=uuid.UUID(test_user["id"]))
    return {"Authorization": f"Bearer {token}"}


# ============================================================================
# Authentication API Tests
# ============================================================================

@pytest.mark.asyncio
class TestAuthenticationAPI:
    """Test authentication endpoints."""
    
    async def test_health_check(self, client: AsyncClient):
        """Test health check endpoint."""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
    
    async def test_register_new_user(self, client: AsyncClient):
        """Test user registration."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "SecurePass123!",
                "full_name": "New User"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "Bearer"
    
    async def test_register_duplicate_email(self, client: AsyncClient, test_user):
        """Test registration with duplicate email."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": test_user["email"],
                "password": "SecurePass123!",
                "full_name": "Duplicate User"
            }
        )
        assert response.status_code == 400
    
    async def test_login_success(self, client: AsyncClient, test_user):
        """Test successful login."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user["email"],
                "password": test_user["password"]
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
    
    async def test_login_invalid_password(self, client: AsyncClient, test_user):
        """Test login with invalid password."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user["email"],
                "password": "WrongPassword123!"
            }
        )
        assert response.status_code == 401
    
    async def test_login_nonexistent_user(self, client: AsyncClient):
        """Test login with non-existent user."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "SomePassword123!"
            }
        )
        assert response.status_code == 401


# ============================================================================
# User API Tests
# ============================================================================

@pytest.mark.asyncio
class TestUserAPI:
    """Test user management endpoints."""
    
    async def test_get_current_user(self, client: AsyncClient, test_user, auth_headers):
        """Test getting current user profile."""
        response = await client.get(
            "/api/v1/users/me",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user["email"]
        assert data["full_name"] == test_user["full_name"]
    
    async def test_get_current_user_unauthorized(self, client: AsyncClient):
        """Test getting current user without authentication."""
        response = await client.get("/api/v1/users/me")
        assert response.status_code == 401
    
    async def test_update_user_profile(self, client: AsyncClient, auth_headers):
        """Test updating user profile."""
        response = await client.patch(
            "/api/v1/users/me",
            headers=auth_headers,
            json={
                "full_name": "Updated Name",
                "timezone": "America/New_York"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "Updated Name"


# ============================================================================
# Exchange API Tests
# ============================================================================

@pytest.mark.asyncio
class TestExchangeAPI:
    """Test exchange connection endpoints."""
    
    async def test_list_exchanges_empty(self, client: AsyncClient, auth_headers):
        """Test listing exchanges when none are connected."""
        response = await client.get(
            "/api/v1/exchanges/connections",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0
    
    async def test_connect_exchange_missing_credentials(self, client: AsyncClient, auth_headers):
        """Test connecting exchange without credentials."""
        response = await client.post(
            "/api/v1/exchanges/connections",
            headers=auth_headers,
            json={
                "exchange_type": "binance",
                "is_testnet": True
            }
        )
        # Should fail due to missing API credentials
        assert response.status_code in [400, 422]


# ============================================================================
# Order API Tests
# ============================================================================

@pytest.mark.asyncio
class TestOrderAPI:
    """Test order management endpoints."""
    
    async def test_list_orders_empty(self, client: AsyncClient, auth_headers):
        """Test listing orders when none exist."""
        response = await client.get(
            "/api/v1/orders/",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "orders" in data
        assert "total" in data
        assert isinstance(data["orders"], list)
        assert len(data["orders"]) == 0
        assert data["total"] == 0
    
    async def test_create_order_validation(self, client: AsyncClient, auth_headers):
        """Test order creation with validation."""
        response = await client.post(
            "/api/v1/orders/",
            headers=auth_headers,
            json={
                "symbol": "BTCUSDT",
                "side": "BUY",
                "order_type": "MARKET",
                "quantity": "0.001"
            }
        )
        # Should fail due to no exchange connection
        assert response.status_code in [400, 422]


# ============================================================================
# Bot API Tests
# ============================================================================

@pytest.mark.asyncio
class TestBotAPI:
    """Test bot management endpoints."""
    
    async def test_list_bots_empty(self, client: AsyncClient, auth_headers):
        """Test listing bots when none exist."""
        response = await client.get(
            "/api/v1/bots/",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0


# ============================================================================
# Market Data API Tests
# ============================================================================

@pytest.mark.asyncio
class TestMarketDataAPI:
    """Test market data endpoints."""
    
    async def test_get_ticker_no_exchange(self, client: AsyncClient, auth_headers):
        """Test getting ticker without exchange connection."""
        response = await client.get(
            "/api/v1/market-data/ticker/BTCUSDT",
            headers=auth_headers
        )
        # Should fail due to no exchange connection
        assert response.status_code in [400, 404]


# ============================================================================
# WebSocket API Tests
# ============================================================================

@pytest.mark.asyncio
class TestWebSocketAPI:
    """Test WebSocket connection endpoints."""
    
    async def test_websocket_connection_requires_auth(self, client: AsyncClient):
        """Test that WebSocket requires authentication."""
        # Note: Testing actual WebSocket connections requires different approach
        # This is a placeholder for WebSocket endpoint existence
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
