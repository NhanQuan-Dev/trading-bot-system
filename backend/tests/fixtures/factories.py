"""Test data factories using Factory pattern."""

from decimal import Decimal
from datetime import datetime, UTC
from uuid import uuid4
from typing import Optional
import random

from faker import Faker

fake = Faker()


class UserFactory:
    """Factory for creating test users."""
    
    @staticmethod
    def build(
        email: Optional[str] = None,
        password: str = "TestPassword123",
        full_name: Optional[str] = None,
        timezone: str = "UTC",
        is_active: bool = True,
    ) -> dict:
        """Build user data."""
        return {
            "id": uuid4(),
            "email": email or fake.email(),
            "password": password,
            "full_name": full_name or fake.name(),
            "timezone": timezone,
            "is_active": is_active,
            "created_at": datetime.now(UTC),
        }


class ExchangeConnectionFactory:
    """Factory for creating test exchange connections."""
    
    @staticmethod
    def build(
        user_id: Optional[str] = None,
        exchange_type: str = "binance",
        testnet: bool = True,
        is_active: bool = True,
    ) -> dict:
        """Build exchange connection data."""
        return {
            "id": uuid4(),
            "user_id": user_id or uuid4(),
            "exchange_type": exchange_type,
            "api_key": fake.sha256()[:32],
            "secret_key": fake.sha256()[:64],
            "testnet": testnet,
            "is_active": is_active,
            "created_at": datetime.now(UTC),
        }


class BotFactory:
    """Factory for creating test bots."""
    
    @staticmethod
    def build(
        user_id: Optional[str] = None,
        exchange_connection_id: Optional[str] = None,
        name: Optional[str] = None,
        strategy_type: str = "grid_trading",
        symbol: str = "BTCUSDT",
        status: str = "stopped",
    ) -> dict:
        """Build bot data."""
        return {
            "id": uuid4(),
            "user_id": user_id or uuid4(),
            "name": name or f"Bot {fake.word()}",
            "strategy_type": strategy_type,
            "exchange_connection_id": exchange_connection_id or uuid4(),
            "symbol": symbol,
            "status": status,
            "configuration": {
                "grid_levels": random.randint(5, 20),
                "grid_size": str(random.randint(50, 200)),
                "quantity_per_grid": str(Decimal(random.uniform(0.001, 0.1))),
            },
            "created_at": datetime.now(UTC),
        }


class OrderFactory:
    """Factory for creating test orders."""
    
    @staticmethod
    def build(
        user_id: Optional[str] = None,
        bot_id: Optional[str] = None,
        symbol: str = "BTCUSDT",
        order_type: str = "limit",
        side: str = "buy",
        quantity: Optional[Decimal] = None,
        price: Optional[Decimal] = None,
        status: str = "new",
    ) -> dict:
        """Build order data."""
        return {
            "id": uuid4(),
            "user_id": user_id or uuid4(),
            "bot_id": bot_id,
            "exchange": "binance",
            "symbol": symbol,
            "order_type": order_type,
            "side": side,
            "quantity": quantity or Decimal(str(random.uniform(0.001, 1.0))),
            "price": price or Decimal(str(random.uniform(30000, 50000))),
            "status": status,
            "created_at": datetime.now(UTC),
        }


class MarketDataFactory:
    """Factory for creating test market data."""
    
    @staticmethod
    def build_candle(
        symbol: str = "BTCUSDT",
        interval: str = "1h",
        open_price: Optional[Decimal] = None,
        close_price: Optional[Decimal] = None,
    ) -> dict:
        """Build candle data."""
        open_val = open_price or Decimal(str(random.uniform(30000, 50000)))
        high_val = open_val + Decimal(str(random.uniform(0, 1000)))
        low_val = open_val - Decimal(str(random.uniform(0, 1000)))
        close_val = close_price or Decimal(str(random.uniform(float(low_val), float(high_val))))
        
        return {
            "id": uuid4(),
            "symbol": symbol,
            "interval": interval,
            "open_time": datetime.now(UTC),
            "open": open_val,
            "high": high_val,
            "low": low_val,
            "close": close_val,
            "volume": Decimal(str(random.uniform(100, 10000))),
            "close_time": datetime.now(UTC),
        }
    
    @staticmethod
    def build_tick(
        symbol: str = "BTCUSDT",
        price: Optional[Decimal] = None,
    ) -> dict:
        """Build tick data."""
        return {
            "symbol": symbol,
            "price": price or Decimal(str(random.uniform(30000, 50000))),
            "quantity": Decimal(str(random.uniform(0.001, 10))),
            "timestamp": datetime.now(UTC),
        }


class RiskLimitFactory:
    """Factory for creating test risk limits."""
    
    @staticmethod
    def build(
        user_id: Optional[str] = None,
        symbol: str = "BTCUSDT",
        limit_type: str = "position_size",
        threshold_value: Optional[Decimal] = None,
        warning_value: Optional[Decimal] = None,
    ) -> dict:
        """Build risk limit data."""
        threshold = threshold_value or Decimal(str(random.uniform(5000, 20000)))
        warning = warning_value or threshold * Decimal("0.8")
        
        return {
            "id": uuid4(),
            "user_id": user_id or uuid4(),
            "symbol": symbol,
            "limit_type": limit_type,
            "threshold_value": threshold,
            "warning_value": warning,
            "enabled": True,
            "created_at": datetime.now(UTC),
        }


class BacktestFactory:
    """Factory for creating test backtests."""
    
    @staticmethod
    def build(
        user_id: Optional[str] = None,
        strategy_id: Optional[str] = None,
        symbol: str = "BTCUSDT",
        initial_capital: Optional[Decimal] = None,
    ) -> dict:
        """Build backtest data."""
        return {
            "id": uuid4(),
            "user_id": user_id or uuid4(),
            "strategy_id": strategy_id or uuid4(),
            "symbol": symbol,
            "start_date": datetime(2024, 1, 1),
            "end_date": datetime(2024, 12, 31),
            "initial_capital": initial_capital or Decimal("10000.00"),
            "status": "pending",
            "created_at": datetime.now(UTC),
        }
