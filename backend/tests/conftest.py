"""Pytest configuration and fixtures."""

import pytest
import asyncio
from typing import AsyncGenerator, Generator, Optional
from decimal import Decimal
from datetime import datetime, timedelta, UTC
from uuid import uuid4, UUID
import os

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy import text
from httpx import AsyncClient, ASGITransport

from src.trading.infrastructure.persistence.database import Base
from src.trading.infrastructure.config.settings import get_settings

# Import all models to register them with Base.metadata
from src.trading.infrastructure.persistence.models import (
    UserModel, ExchangeModel, APIConnectionModel, DatabaseConfigModel, SymbolModel,
    OrderModel, PositionModel, TradeModel,
    BotModel, StrategyModel, BacktestModel, BotPerformanceModel,
    BacktestRunModel, BacktestResultModel, BacktestTradeModel,
    MarketPriceModel, OrderBookSnapshotModel,
    RiskLimitModel, RiskAlertModel, AlertModel, EventQueueModel,
)


# Test database URL
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://test_user:test_password@localhost:5433/trading_test"
)

# Test Redis URL
TEST_REDIS_URL = os.getenv("TEST_REDIS_URL", "redis://localhost:6380/0")

# Track test run IDs for cleanup
_test_run_data = set()


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
async def test_engine():
    """Create test database engine per module for better isolation."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=NullPool,
        echo=False,
    )
    
    # Create all tables (if not exist, idempotent)
    # This ensures tables exist even if dropped by previous module
    async with engine.begin() as conn:
        # Ensure all models are imported before creating tables
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Dispose engine after each module
    await engine.dispose()


@pytest.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create database session for tests."""
    async_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with async_session() as session:
        yield session
        # Rollback any uncommitted changes
        await session.rollback()


@pytest.fixture
def sample_user_id():
    """Sample user ID."""
    return uuid4()


@pytest.fixture
def sample_strategy_id():
    """Sample strategy ID."""
    return uuid4()


@pytest.fixture
def sample_backtest_config():
    """Sample backtest configuration."""
    from src.trading.domain.backtesting import BacktestConfig
    
    return BacktestConfig(
        mode="event_driven",
        initial_capital=Decimal("10000"),
        slippage_model="fixed",
        slippage_percent=Decimal("0.001"),
        commission_model="fixed_rate",
        commission_percent=Decimal("0.001"),
    )


@pytest.fixture
def sample_candles():
    """Sample candle data for backtesting."""
    base_time = datetime(2024, 1, 1, 0, 0, 0)
    candles = []
    
    price = 42000.0
    for i in range(100):
        # Simple price movement
        price += (i % 10 - 5) * 100
        
        candles.append({
            "timestamp": (base_time + timedelta(hours=i)).isoformat(),
            "open": price - 50,
            "high": price + 100,
            "low": price - 100,
            "close": price,
            "volume": 10.5,
        })
    
    return candles


@pytest.fixture
def simple_strategy():
    """Simple moving average crossover strategy."""
    def strategy_func(candle, idx, position):
        """Buy when price above 42000, sell when below."""
        if idx < 5:
            return None
        
        close = candle.get("close", 0)
        
        if close > 42000:
            if not position:
                return {"type": "buy", "stop_loss": close * 0.95, "take_profit": close * 1.05}
        else:
            if position:
                return {"type": "close"}
        
        return None
    
    return strategy_func


# ===== User & Authentication Fixtures =====

@pytest.fixture
async def test_user(db_session: AsyncSession):
    """Create a test user in database with attribute and key access."""
    from src.trading.infrastructure.persistence.models.core_models import UserModel
    from src.trading.domain.user import HashedPassword

    user_id = uuid4()
    plain_password = "TestPassword123"
    hashed_password = HashedPassword.from_plain(plain_password)
    
    # Use UUID to ensure unique email for each test
    unique_id = str(uuid4())[:8]
    unique_email = f"test_{unique_id}@example.com"
    
    user = UserModel(
        id=user_id,
        email=unique_email,
        password_hash=hashed_password.value,
        full_name="Test User",
        timezone="UTC",
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC)
    )
    
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    class AttrDict(dict):
        """Dict with attribute access for test fixtures."""
        def __getattr__(self, item):
            try:
                return self[item]
            except KeyError:
                raise AttributeError(item)

    return AttrDict(
        id=user.id,
        email=user.email,
        password=plain_password,
        full_name=user.full_name,
        timezone=user.timezone,
    )


@pytest.fixture
async def test_user_2(db_session: AsyncSession):
    """Create a second test user with unique email."""
    from src.trading.infrastructure.persistence.models.core_models import UserModel
    from src.trading.domain.user import HashedPassword

    # Use UUID to ensure unique email for each test
    unique_id = str(uuid4())[:8]
    unique_email = f"test2_{unique_id}@example.com"

    user = UserModel(
        id=uuid4(),
        email=unique_email,
        password_hash=HashedPassword.from_plain("TestPassword123").value,
        full_name="Test User 2",
        timezone="UTC",
        is_active=True,
        created_at=datetime.now(UTC),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def auth_headers(test_user):
    """Generate authentication headers with JWT token."""
    from src.trading.infrastructure.auth.jwt import create_access_token
    import uuid
    
    user_id = uuid.UUID(test_user["id"]) if isinstance(test_user["id"], str) else test_user["id"]
    access_token = create_access_token(user_id)
    
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
async def test_client(test_engine):
    """Create async HTTP client for API testing."""
    from src.main import create_app
    
    app = create_app()
    
    # Override database dependency
    from src.trading.infrastructure.persistence.database import get_db
    
    async def override_get_session():
        async_session = async_sessionmaker(
            test_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        async with async_session() as session:
            yield session
    
    app.dependency_overrides[get_db] = override_get_session
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


# ===== Exchange Connection Fixtures =====

@pytest.fixture
async def test_exchange_connection(db_session: AsyncSession, test_user):
    """Create test exchange connection."""
    from src.trading.infrastructure.persistence.models.exchange import ExchangeConnectionModel
    from cryptography.fernet import Fernet
    
    # Generate test encryption key
    key = Fernet.generate_key()
    cipher = Fernet(key)
    
    connection = ExchangeConnectionModel(
        id=uuid4(),
        user_id=test_user.id,
        exchange_type="binance",
        api_key_encrypted=cipher.encrypt(b"test_api_key").decode(),
        secret_key_encrypted=cipher.encrypt(b"test_secret_key").decode(),
        testnet=True,
        is_active=True,
        created_at=datetime.now(UTC),
    )
    db_session.add(connection)
    await db_session.commit()
    await db_session.refresh(connection)
    return connection


# ===== Bot Fixtures =====

@pytest.fixture
async def test_bot(db_session: AsyncSession, test_user, test_exchange_connection):
    """Create test trading bot."""
    from src.trading.infrastructure.persistence.models.bot import BotModel
    
    bot = BotModel(
        id=uuid4(),
        user_id=test_user.id,
        name="Test Bot",
        strategy_type="grid_trading",
        exchange_connection_id=test_exchange_connection.id,
        symbol="BTCUSDT",
        status="stopped",
        configuration={
            "grid_levels": 10,
            "grid_size": "100",
            "quantity_per_grid": "0.01"
        },
        created_at=datetime.now(UTC),
    )
    db_session.add(bot)
    await db_session.commit()
    await db_session.refresh(bot)
    return bot


# ===== Order Fixtures =====

@pytest.fixture
async def test_order(db_session: AsyncSession, test_user, test_bot):
    """Create test order."""
    from src.trading.infrastructure.persistence.models.order import OrderModel
    
    order = OrderModel(
        id=uuid4(),
        user_id=test_user.id,
        bot_id=test_bot.id,
        exchange="binance",
        symbol="BTCUSDT",
        order_type="limit",
        side="buy",
        quantity=Decimal("0.01"),
        price=Decimal("42000.00"),
        status="new",
        created_at=datetime.now(UTC),
    )
    db_session.add(order)
    await db_session.commit()
    await db_session.refresh(order)
    return order


# ===== Market Data Fixtures =====

@pytest.fixture
async def test_subscription(db_session: AsyncSession, test_user):
    """Create test market data subscription."""
    from src.trading.infrastructure.persistence.models.market_data import MarketDataSubscriptionModel
    
    subscription = MarketDataSubscriptionModel(
        id=uuid4(),
        user_id=test_user.id,
        data_type="candle",
        symbol="BTCUSDT",
        interval="1h",
        status="active",
        created_at=datetime.now(UTC),
    )
    db_session.add(subscription)
    await db_session.commit()
    await db_session.refresh(subscription)
    return subscription


# ===== Risk Management Fixtures =====

@pytest.fixture
async def test_risk_limit(db_session: AsyncSession, test_user):
    """Create test risk limit."""
    from src.trading.infrastructure.persistence.models.risk import RiskLimitModel
    
    risk_limit = RiskLimitModel(
        id=uuid4(),
        user_id=test_user.id,
        symbol="BTCUSDT",
        limit_type="position_size",
        threshold_value=Decimal("10000.00"),
        warning_value=Decimal("8000.00"),
        enabled=True,
        created_at=datetime.now(UTC),
    )
    db_session.add(risk_limit)
    await db_session.commit()
    await db_session.refresh(risk_limit)
    return risk_limit


# ===== Mock Services =====

@pytest.fixture
def mock_binance_client(monkeypatch):
    """Mock Binance API client."""
    from unittest.mock import AsyncMock, MagicMock
    
    mock_client = AsyncMock()
    mock_client.get_account.return_value = {
        "balances": [
            {"asset": "USDT", "free": "10000.00", "locked": "0.00"},
            {"asset": "BTC", "free": "0.5", "locked": "0.00"},
        ]
    }
    mock_client.get_positions.return_value = []
    mock_client.place_order.return_value = {
        "orderId": 12345,
        "symbol": "BTCUSDT",
        "status": "NEW",
        "side": "BUY",
        "type": "LIMIT",
        "price": "42000.00",
        "origQty": "0.01",
    }
    
    return mock_client


@pytest.fixture
def mock_redis_client(monkeypatch):
    """Mock Redis client."""
    from unittest.mock import AsyncMock
    
    mock_redis = AsyncMock()
    mock_redis.get.return_value = None
    mock_redis.set.return_value = True
    mock_redis.delete.return_value = 1
    mock_redis.exists.return_value = False
    mock_redis.ping.return_value = True
    
    return mock_redis
