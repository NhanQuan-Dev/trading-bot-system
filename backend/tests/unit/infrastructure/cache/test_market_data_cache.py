"""Test cases for MarketDataCache."""
import pytest
from unittest.mock import AsyncMock
from datetime import datetime
import json

from src.trading.infrastructure.cache.market_data_cache import MarketDataCache


class TestMarketDataCache:
    """Test cases for MarketDataCache implementation."""
    
    @pytest.fixture
    def mock_redis(self):
        """Create mock Redis client."""
        redis_mock = AsyncMock()
        redis_mock.get = AsyncMock(return_value=None)
        redis_mock.set = AsyncMock(return_value=True)
        redis_mock.lpush = AsyncMock(return_value=1)
        redis_mock.ltrim = AsyncMock(return_value=True)
        redis_mock.lrange = AsyncMock(return_value=[])
        redis_mock.expire = AsyncMock(return_value=True)
        redis_mock.keys = AsyncMock(return_value=[])
        redis_mock.ttl = AsyncMock(return_value=60)
        return redis_mock
    
    @pytest.fixture
    def market_cache(self, mock_redis):
        """Create MarketDataCache instance with mocked Redis."""
        cache = MarketDataCache()
        cache.redis = mock_redis
        return cache
    
    def test_init(self, market_cache):
        """Test MarketDataCache initialization."""
        assert market_cache.prefix == "market"
        assert market_cache.default_ttl == 60  # 1 minute
    
    @pytest.mark.asyncio
    async def test_set_symbol_price_with_timestamp(self, market_cache, mock_redis):
        """Test setting symbol price with timestamp."""
        price_data = {
            "price": 50000.0,
            "volume": 1000.0,
            "timestamp": "2024-01-15T12:00:00"
        }
        
        result = await market_cache.set_symbol_price("BTCUSDT", price_data, ttl=30)
        
        assert result is True
        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args
        assert call_args[0][0] == "market:price:BTCUSDT"
        assert call_args[1]["ex"] == 30
    
    @pytest.mark.asyncio
    async def test_set_symbol_price_auto_timestamp(self, market_cache, mock_redis):
        """Test setting symbol price with automatic timestamp."""
        price_data = {"price": 50000.0, "volume": 1000.0}
        
        result = await market_cache.set_symbol_price("BTCUSDT", price_data, ttl=30)
        
        assert result is True
        # Verify timestamp was added
        call_args = mock_redis.set.call_args
        stored_data = json.loads(call_args[0][1])
        assert "timestamp" in stored_data
        assert stored_data["price"] == 50000.0
    
    @pytest.mark.asyncio
    async def test_get_symbol_price(self, market_cache, mock_redis):
        """Test getting symbol price."""
        price_data = {
            "price": 50000.0,
            "volume": 1000.0,
            "timestamp": "2024-01-15T12:00:00"
        }
        mock_redis.get.return_value = json.dumps(price_data)
        
        result = await market_cache.get_symbol_price("BTCUSDT")
        
        assert result == price_data
        mock_redis.get.assert_called_once_with("market:price:BTCUSDT")
    
    @pytest.mark.asyncio
    async def test_set_symbol_prices(self, market_cache, mock_redis):
        """Test setting multiple symbol prices."""
        prices = {
            "BTCUSDT": {"price": 50000.0, "volume": 1000.0},
            "ETHUSDT": {"price": 3000.0, "volume": 500.0}
        }
        
        results = await market_cache.set_symbol_prices(prices, ttl=60)
        
        assert len(results) == 2
        assert results["BTCUSDT"] is True
        assert results["ETHUSDT"] is True
        assert mock_redis.set.call_count == 2
    
    @pytest.mark.asyncio
    async def test_get_symbol_prices(self, market_cache, mock_redis):
        """Test getting multiple symbol prices."""
        async def mock_get_side_effect(key):
            if key == "market:price:BTCUSDT":
                return json.dumps({"price": 50000.0})
            elif key == "market:price:ETHUSDT":
                return json.dumps({"price": 3000.0})
            return None
        
        mock_redis.get.side_effect = mock_get_side_effect
        
        result = await market_cache.get_symbol_prices(["BTCUSDT", "ETHUSDT", "UNKNOWN"])
        
        assert len(result) == 2
        assert "BTCUSDT" in result
        assert "ETHUSDT" in result
        assert "UNKNOWN" not in result
    
    @pytest.mark.asyncio
    async def test_set_order_book(self, market_cache, mock_redis):
        """Test setting order book."""
        order_book = {
            "bids": [[50000.0, 1.0], [49990.0, 2.0]],
            "asks": [[50010.0, 1.5], [50020.0, 2.5]]
        }
        
        result = await market_cache.set_order_book("BTCUSDT", order_book, ttl=10)
        
        assert result is True
        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args
        assert call_args[0][0] == "market:orderbook:BTCUSDT"
        assert call_args[1]["ex"] == 10
        
        # Verify timestamp was added
        stored_data = json.loads(call_args[0][1])
        assert "timestamp" in stored_data
        assert "bids" in stored_data
        assert "asks" in stored_data
    
    @pytest.mark.asyncio
    async def test_get_order_book(self, market_cache, mock_redis):
        """Test getting order book."""
        order_book = {
            "bids": [[50000.0, 1.0]],
            "asks": [[50010.0, 1.5]],
            "timestamp": "2024-01-15T12:00:00"
        }
        mock_redis.get.return_value = json.dumps(order_book)
        
        result = await market_cache.get_order_book("BTCUSDT")
        
        assert result == order_book
        mock_redis.get.assert_called_once_with("market:orderbook:BTCUSDT")
    
    @pytest.mark.asyncio
    async def test_set_trade(self, market_cache, mock_redis):
        """Test setting recent trade."""
        trade_data = {
            "price": 50000.0,
            "quantity": 0.5,
            "side": "BUY"
        }
        
        result = await market_cache.set_trade("BTCUSDT", trade_data, ttl=300)
        
        assert result is True
        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args
        assert call_args[0][0] == "market:trade:BTCUSDT:latest"
    
    @pytest.mark.asyncio
    async def test_get_trade(self, market_cache, mock_redis):
        """Test getting latest trade."""
        trade_data = {
            "price": 50000.0,
            "quantity": 0.5,
            "side": "BUY",
            "timestamp": "2024-01-15T12:00:00"
        }
        mock_redis.get.return_value = json.dumps(trade_data)
        
        result = await market_cache.get_trade("BTCUSDT")
        
        assert result == trade_data
        mock_redis.get.assert_called_once_with("market:trade:BTCUSDT:latest")
    
    @pytest.mark.asyncio
    async def test_add_trade_history(self, market_cache, mock_redis):
        """Test adding trade to history."""
        trade_data = {
            "price": 50000.0,
            "quantity": 0.5,
            "side": "BUY",
            "timestamp": "2024-01-15T12:00:00"
        }
        
        result = await market_cache.add_trade_history("BTCUSDT", trade_data, max_trades=100)
        
        assert result is True
        # Verify lpush was called
        mock_redis.lpush.assert_called_once()
        # Verify ltrim was called to limit history
        mock_redis.ltrim.assert_called_once()
        # Verify expiration was set
        mock_redis.expire.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_trade_history(self, market_cache, mock_redis):
        """Test getting trade history."""
        trades = [
            {"price": 50000.0, "quantity": 0.5, "side": "BUY"},
            {"price": 50010.0, "quantity": 0.3, "side": "SELL"}
        ]
        mock_redis.lrange.return_value = [json.dumps(trade) for trade in trades]
        
        result = await market_cache.get_trade_history("BTCUSDT", limit=50)
        
        assert len(result) == 2
        assert result[0]["price"] == 50000.0
        assert result[1]["price"] == 50010.0
        mock_redis.lrange.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_trade_history_empty(self, market_cache, mock_redis):
        """Test getting trade history when empty."""
        mock_redis.lrange.return_value = []
        
        result = await market_cache.get_trade_history("UNKNOWN", limit=10)
        assert result == []
    
    @pytest.mark.asyncio
    async def test_set_24h_stats(self, market_cache, mock_redis):
        """Test setting 24h statistics."""
        stats = {
            "high": 52000.0,
            "low": 48000.0,
            "volume": 100000.0,
            "price_change_percent": 2.5
        }
        
        result = await market_cache.set_24h_stats("BTCUSDT", stats, ttl=300)
        
        assert result is True
        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args
        assert call_args[0][0] == "market:stats24h:BTCUSDT"
        
        # Verify timestamp was added
        stored_data = json.loads(call_args[0][1])
        assert "timestamp" in stored_data
        assert stored_data["high"] == 52000.0
