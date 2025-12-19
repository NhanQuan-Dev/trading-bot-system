import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Optional, Any, Dict, List, Union
from datetime import datetime, timedelta
import json

from .redis_client import redis_client

logger = logging.getLogger(__name__)


class BaseCache(ABC):
    """Base class for cache implementations."""
    
    def __init__(self, prefix: str = "", default_ttl: int = 3600):
        self.prefix = prefix
        self.default_ttl = default_ttl
        self.redis = redis_client
    
    def _make_key(self, key: str) -> str:
        """Generate cache key with prefix."""
        if self.prefix:
            return f"{self.prefix}:{key}"
        return key
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        cache_key = self._make_key(key)
        try:
            data = await self.redis.get(cache_key)
            if data is None:
                return None
            return self._deserialize(data)
        except Exception as e:
            logger.error(f"Cache GET error for key {cache_key}: {e}")
            return None
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        ttl: Optional[int] = None
    ) -> bool:
        """Set value in cache."""
        cache_key = self._make_key(key)
        ttl = ttl or self.default_ttl
        
        try:
            serialized = self._serialize(value)
            return await self.redis.set(cache_key, serialized, ex=ttl)
        except Exception as e:
            logger.error(f"Cache SET error for key {cache_key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        cache_key = self._make_key(key)
        try:
            result = await self.redis.delete(cache_key)
            return bool(result)
        except Exception as e:
            logger.error(f"Cache DELETE error for key {cache_key}: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        cache_key = self._make_key(key)
        try:
            return await self.redis.exists(cache_key)
        except Exception as e:
            logger.error(f"Cache EXISTS error for key {cache_key}: {e}")
            return False
    
    async def expire(self, key: str, ttl: int) -> bool:
        """Set expiration time for key."""
        cache_key = self._make_key(key)
        try:
            return await self.redis.expire(cache_key, ttl)
        except Exception as e:
            logger.error(f"Cache EXPIRE error for key {cache_key}: {e}")
            return False
    
    async def ttl(self, key: str) -> int:
        """Get time to live for key."""
        cache_key = self._make_key(key)
        try:
            return await self.redis.ttl(cache_key)
        except Exception as e:
            logger.error(f"Cache TTL error for key {cache_key}: {e}")
            return -1
    
    async def get_or_set(
        self, 
        key: str, 
        factory, 
        ttl: Optional[int] = None
    ) -> Any:
        """Get value from cache or set it using factory function."""
        value = await self.get(key)
        if value is not None:
            return value
        
        # Generate value using factory
        if asyncio.iscoroutinefunction(factory):
            value = await factory()
        else:
            value = factory()
        
        if value is not None:
            await self.set(key, value, ttl)
        
        return value
    
    async def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple values from cache."""
        result = {}
        for key in keys:
            value = await self.get(key)
            if value is not None:
                result[key] = value
        return result
    
    async def set_many(
        self, 
        data: Dict[str, Any], 
        ttl: Optional[int] = None
    ) -> Dict[str, bool]:
        """Set multiple values in cache."""
        results = {}
        for key, value in data.items():
            results[key] = await self.set(key, value, ttl)
        return results
    
    async def delete_many(self, keys: List[str]) -> Dict[str, bool]:
        """Delete multiple keys from cache."""
        results = {}
        for key in keys:
            results[key] = await self.delete(key)
        return results
    
    async def clear_prefix(self, pattern: str = "*") -> int:
        """Clear all keys matching pattern within prefix."""
        search_pattern = self._make_key(pattern)
        try:
            keys = await self.redis.keys(search_pattern)
            if keys:
                return await self.redis.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Cache CLEAR_PREFIX error for pattern {search_pattern}: {e}")
            return 0
    
    def _serialize(self, value: Any) -> str:
        """Serialize value for storage."""
        if isinstance(value, str):
            return value
        return json.dumps(value, default=str)
    
    def _deserialize(self, value: str) -> Any:
        """Deserialize value from storage."""
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        try:
            pattern = self._make_key("*")
            keys = await self.redis.keys(pattern)
            
            stats = {
                "total_keys": len(keys),
                "prefix": self.prefix,
                "default_ttl": self.default_ttl,
                "keys_with_ttl": 0,
                "keys_without_ttl": 0,
            }
            
            # Check TTL for each key
            for key in keys[:100]:  # Limit to prevent performance issues
                ttl = await self.redis.ttl(key)
                if ttl > 0:
                    stats["keys_with_ttl"] += 1
                else:
                    stats["keys_without_ttl"] += 1
            
            return stats
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {"error": str(e)}