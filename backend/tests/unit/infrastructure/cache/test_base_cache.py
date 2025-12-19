"""Test cases for BaseCache."""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any
import json

from src.trading.infrastructure.cache.base_cache import BaseCache


class TestBaseCache:
    """Test cases for BaseCache implementation."""
    
    @pytest.fixture
    def mock_redis(self):
        """Create mock Redis client."""
        redis_mock = AsyncMock()
        redis_mock.get = AsyncMock(return_value=None)
        redis_mock.set = AsyncMock(return_value=True)
        redis_mock.delete = AsyncMock(return_value=1)
        redis_mock.exists = AsyncMock(return_value=False)
        redis_mock.expire = AsyncMock(return_value=True)
        redis_mock.ttl = AsyncMock(return_value=3600)
        redis_mock.keys = AsyncMock(return_value=[])
        return redis_mock
    
    @pytest.fixture
    def cache(self, mock_redis):
        """Create BaseCache instance with mocked Redis."""
        cache = BaseCache(prefix="test", default_ttl=60)
        cache.redis = mock_redis
        return cache
    
    def test_init_with_prefix(self):
        """Test cache initialization with prefix."""
        cache = BaseCache(prefix="myprefix", default_ttl=120)
        assert cache.prefix == "myprefix"
        assert cache.default_ttl == 120
    
    def test_init_without_prefix(self):
        """Test cache initialization without prefix."""
        cache = BaseCache(prefix="", default_ttl=300)
        assert cache.prefix == ""
        assert cache.default_ttl == 300
    
    def test_make_key_with_prefix(self, cache):
        """Test key generation with prefix."""
        key = cache._make_key("mykey")
        assert key == "test:mykey"
    
    def test_make_key_without_prefix(self):
        """Test key generation without prefix."""
        cache = BaseCache(prefix="", default_ttl=60)
        key = cache._make_key("mykey")
        assert key == "mykey"
    
    @pytest.mark.asyncio
    async def test_set_success(self, cache, mock_redis):
        """Test successful set operation."""
        result = await cache.set("key1", {"data": "value"}, ttl=120)
        
        assert result is True
        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args
        assert call_args[0][0] == "test:key1"  # Prefixed key
        assert json.loads(call_args[0][1]) == {"data": "value"}
        assert call_args[1]["ex"] == 120
    
    @pytest.mark.asyncio
    async def test_set_with_default_ttl(self, cache, mock_redis):
        """Test set operation with default TTL."""
        result = await cache.set("key1", "value1")
        
        assert result is True
        call_args = mock_redis.set.call_args
        assert call_args[1]["ex"] == 60  # Default TTL
    
    @pytest.mark.asyncio
    async def test_set_string_value(self, cache, mock_redis):
        """Test set operation with string value."""
        result = await cache.set("key1", "simple_string", ttl=30)
        
        assert result is True
        call_args = mock_redis.set.call_args
        assert call_args[0][1] == "simple_string"  # Not JSON serialized
    
    @pytest.mark.asyncio
    async def test_set_failure(self, cache, mock_redis):
        """Test set operation failure."""
        mock_redis.set.side_effect = Exception("Redis error")
        
        result = await cache.set("key1", "value1")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_get_success(self, cache, mock_redis):
        """Test successful get operation."""
        mock_redis.get.return_value = '{"data": "value"}'
        
        result = await cache.get("key1")
        
        assert result == {"data": "value"}
        mock_redis.get.assert_called_once_with("test:key1")
    
    @pytest.mark.asyncio
    async def test_get_string_value(self, cache, mock_redis):
        """Test get operation with string value."""
        mock_redis.get.return_value = "simple_string"
        
        result = await cache.get("key1")
        assert result == "simple_string"
    
    @pytest.mark.asyncio
    async def test_get_not_found(self, cache, mock_redis):
        """Test get operation when key not found."""
        mock_redis.get.return_value = None
        
        result = await cache.get("nonexistent")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_failure(self, cache, mock_redis):
        """Test get operation failure."""
        mock_redis.get.side_effect = Exception("Redis error")
        
        result = await cache.get("key1")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_delete_success(self, cache, mock_redis):
        """Test successful delete operation."""
        mock_redis.delete.return_value = 1
        
        result = await cache.delete("key1")
        
        assert result is True
        mock_redis.delete.assert_called_once_with("test:key1")
    
    @pytest.mark.asyncio
    async def test_delete_not_found(self, cache, mock_redis):
        """Test delete operation when key not found."""
        mock_redis.delete.return_value = 0
        
        result = await cache.delete("nonexistent")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_delete_failure(self, cache, mock_redis):
        """Test delete operation failure."""
        mock_redis.delete.side_effect = Exception("Redis error")
        
        result = await cache.delete("key1")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_exists_true(self, cache, mock_redis):
        """Test exists operation when key exists."""
        mock_redis.exists.return_value = True
        
        result = await cache.exists("key1")
        
        assert result is True
        mock_redis.exists.assert_called_once_with("test:key1")
    
    @pytest.mark.asyncio
    async def test_exists_false(self, cache, mock_redis):
        """Test exists operation when key does not exist."""
        mock_redis.exists.return_value = False
        
        result = await cache.exists("nonexistent")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_expire_success(self, cache, mock_redis):
        """Test successful expire operation."""
        mock_redis.expire.return_value = True
        
        result = await cache.expire("key1", 300)
        
        assert result is True
        mock_redis.expire.assert_called_once_with("test:key1", 300)
    
    @pytest.mark.asyncio
    async def test_ttl_success(self, cache, mock_redis):
        """Test successful TTL retrieval."""
        mock_redis.ttl.return_value = 1800
        
        result = await cache.ttl("key1")
        
        assert result == 1800
        mock_redis.ttl.assert_called_once_with("test:key1")
    
    @pytest.mark.asyncio
    async def test_ttl_failure(self, cache, mock_redis):
        """Test TTL retrieval failure."""
        mock_redis.ttl.side_effect = Exception("Redis error")
        
        result = await cache.ttl("key1")
        assert result == -1
    
    @pytest.mark.asyncio
    async def test_get_or_set_cached(self, cache, mock_redis):
        """Test get_or_set when value is cached."""
        mock_redis.get.return_value = '"cached_value"'
        factory = Mock(return_value="new_value")
        
        result = await cache.get_or_set("key1", factory, ttl=60)
        
        assert result == "cached_value"
        factory.assert_not_called()  # Factory should not be called
        mock_redis.set.assert_not_called()  # Should not set new value
    
    @pytest.mark.asyncio
    async def test_get_or_set_not_cached_sync_factory(self, cache, mock_redis):
        """Test get_or_set when value not cached with sync factory."""
        mock_redis.get.return_value = None
        factory = Mock(return_value="new_value")
        
        result = await cache.get_or_set("key1", factory, ttl=60)
        
        assert result == "new_value"
        factory.assert_called_once()
        mock_redis.set.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_or_set_not_cached_async_factory(self, cache, mock_redis):
        """Test get_or_set when value not cached with async factory."""
        mock_redis.get.return_value = None
        factory = AsyncMock(return_value="async_value")
        
        result = await cache.get_or_set("key1", factory, ttl=60)
        
        assert result == "async_value"
        factory.assert_called_once()
        mock_redis.set.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_many(self, cache, mock_redis):
        """Test get_many operation."""
        async def mock_get_side_effect(key):
            if key == "test:key1":
                return '"value1"'
            elif key == "test:key2":
                return '"value2"'
            return None
        
        mock_redis.get.side_effect = mock_get_side_effect
        
        result = await cache.get_many(["key1", "key2", "key3"])
        
        assert result == {"key1": "value1", "key2": "value2"}
        assert "key3" not in result
    
    @pytest.mark.asyncio
    async def test_set_many(self, cache, mock_redis):
        """Test set_many operation."""
        data = {"key1": "value1", "key2": "value2"}
        
        results = await cache.set_many(data, ttl=120)
        
        assert results == {"key1": True, "key2": True}
        assert mock_redis.set.call_count == 2
    
    @pytest.mark.asyncio
    async def test_delete_many(self, cache, mock_redis):
        """Test delete_many operation."""
        mock_redis.delete.return_value = 1
        
        results = await cache.delete_many(["key1", "key2", "key3"])
        
        assert results == {"key1": True, "key2": True, "key3": True}
        assert mock_redis.delete.call_count == 3
    
    @pytest.mark.asyncio
    async def test_clear_prefix(self, cache, mock_redis):
        """Test clear_prefix operation."""
        mock_redis.keys.return_value = ["test:key1", "test:key2", "test:key3"]
        mock_redis.delete.return_value = 3
        
        count = await cache.clear_prefix("*")
        
        assert count == 3
        mock_redis.keys.assert_called_once_with("test:*")
        mock_redis.delete.assert_called_once_with("test:key1", "test:key2", "test:key3")
    
    @pytest.mark.asyncio
    async def test_clear_prefix_no_keys(self, cache, mock_redis):
        """Test clear_prefix when no keys match."""
        mock_redis.keys.return_value = []
        
        count = await cache.clear_prefix("*")
        
        assert count == 0
        mock_redis.delete.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_get_stats(self, cache, mock_redis):
        """Test get_stats operation."""
        mock_redis.keys.return_value = ["test:key1", "test:key2", "test:key3"]
        
        async def mock_ttl_side_effect(key):
            if key == "test:key1":
                return 300  # Has TTL
            elif key == "test:key2":
                return -1   # No TTL
            return 100
        
        mock_redis.ttl.side_effect = mock_ttl_side_effect
        
        stats = await cache.get_stats()
        
        assert stats["total_keys"] == 3
        assert stats["prefix"] == "test"
        assert stats["default_ttl"] == 60
        assert stats["keys_with_ttl"] == 2
        assert stats["keys_without_ttl"] == 1
