import asyncio
import logging
from typing import Optional, Any, Dict, List, Union
import redis.asyncio as redis
import json
from datetime import datetime, timedelta

from ..config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class RedisClient:
    """Async Redis client wrapper with enhanced functionality."""
    
    def __init__(self):
        self._redis: Optional[redis.Redis] = None
        self._connection_pool: Optional[redis.ConnectionPool] = None
        self._is_connected = False
        
    async def connect(self):
        """Establish Redis connection."""
        if self._is_connected:
            return
        
        try:
            # Create connection pool
            self._connection_pool = redis.ConnectionPool(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                password=settings.REDIS_PASSWORD,
                decode_responses=True,
                max_connections=settings.REDIS_MAX_CONNECTIONS,
                retry_on_timeout=True,
                health_check_interval=30,
            )
            
            # Create Redis client
            self._redis = redis.Redis(
                connection_pool=self._connection_pool,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
            
            # Test connection
            await self._redis.ping()
            self._is_connected = True
            
            logger.info("Redis connected successfully")
            
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self._is_connected = False
            raise
    
    async def disconnect(self):
        """Close Redis connection."""
        if self._redis:
            await self._redis.aclose()
            self._redis = None
        
        if self._connection_pool:
            await self._connection_pool.aclose()
            self._connection_pool = None
        
        self._is_connected = False
        logger.info("Redis disconnected")
    
    async def ensure_connected(self):
        """Ensure Redis is connected, reconnect if necessary."""
        if not self._is_connected or not self._redis:
            await self.connect()
    
    async def zrangebyscore(self, key: str, min_score: float, max_score: float, withscores: bool = False, start: int = 0, num: int = -1):
        """Get sorted set members by score range."""
        await self.ensure_connected()
        try:
            if withscores:
                return await self._redis.zrangebyscore(key, min_score, max_score, start=start, num=num, withscores=True)
            else:
                return await self._redis.zrangebyscore(key, min_score, max_score, start=start, num=num)
        except AttributeError as e:
            logger.error(f"Redis client not properly initialized: {e}")
            return []
        except Exception as e:
            logger.error(f"Redis ZRANGEBYSCORE error for key {key}: {e}")
            return []
    
    async def zrem(self, key: str, *members) -> int:
        """Remove members from sorted set."""
        await self.ensure_connected()
        try:
            return await self._redis.zrem(key, *members)
        except Exception as e:
            logger.error(f"Redis ZREM error for key {key}: {e}")
            return 0
    
    async def rpush(self, key: str, *values) -> int:
        """Push values to end of list."""
        await self.ensure_connected()
        try:
            return await self._redis.rpush(key, *values)
        except Exception as e:
            logger.error(f"Redis RPUSH error for key {key}: {e}")
            return 0
    
    async def lpop(self, key: str) -> Optional[str]:
        """Remove and return first element of list."""
        await self.ensure_connected()
        try:
            return await self._redis.lpop(key)
        except Exception as e:
            logger.error(f"Redis LPOP error for key {key}: {e}")
            return None
    
    async def llen(self, key: str) -> int:
        """Get length of list."""
        await self.ensure_connected()
        try:
            return await self._redis.llen(key)
        except Exception as e:
            logger.error(f"Redis LLEN error for key {key}: {e}")
            return 0
    
    async def zadd(self, key: str, mapping: Dict[str, float]) -> int:
        """Add members to sorted set."""
        await self.ensure_connected()
        try:
            return await self._redis.zadd(key, mapping)
        except Exception as e:
            logger.error(f"Redis ZADD error for key {key}: {e}")
            return 0
    
    async def zcard(self, key: str) -> int:
        """Get cardinality of sorted set."""
        await self.ensure_connected()
        try:
            return await self._redis.zcard(key)
        except Exception as e:
            logger.error(f"Redis ZCARD error for key {key}: {e}")
            return 0
    
    async def get(self, key: str) -> Optional[str]:
        """Get value from Redis."""
        await self.ensure_connected()
        try:
            return await self._redis.get(key)
        except Exception as e:
            logger.error(f"Redis GET error for key {key}: {e}")
            return None
    
    async def set(
        self, 
        key: str, 
        value: str, 
        ex: Optional[int] = None,
        px: Optional[int] = None,
        nx: bool = False,
        xx: bool = False
    ) -> bool:
        """Set value in Redis."""
        await self.ensure_connected()
        try:
            result = await self._redis.set(key, value, ex=ex, px=px, nx=nx, xx=xx)
            return bool(result)
        except Exception as e:
            logger.error(f"Redis SET error for key {key}: {e}")
            return False
    
    async def delete(self, *keys: str) -> int:
        """Delete keys from Redis."""
        await self.ensure_connected()
        try:
            return await self._redis.delete(*keys)
        except Exception as e:
            logger.error(f"Redis DELETE error for keys {keys}: {e}")
            return 0
    
    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        await self.ensure_connected()
        try:
            return bool(await self._redis.exists(key))
        except Exception as e:
            logger.error(f"Redis EXISTS error for key {key}: {e}")
            return False
    
    async def expire(self, key: str, time: int) -> bool:
        """Set key expiration time."""
        await self.ensure_connected()
        try:
            return bool(await self._redis.expire(key, time))
        except Exception as e:
            logger.error(f"Redis EXPIRE error for key {key}: {e}")
            return False
    
    async def ttl(self, key: str) -> int:
        """Get time to live for key."""
        await self.ensure_connected()
        try:
            return await self._redis.ttl(key)
        except Exception as e:
            logger.error(f"Redis TTL error for key {key}: {e}")
            return -1
    
    async def hget(self, name: str, key: str) -> Optional[str]:
        """Get field value from hash."""
        await self.ensure_connected()
        try:
            return await self._redis.hget(name, key)
        except Exception as e:
            logger.error(f"Redis HGET error for hash {name}, key {key}: {e}")
            return None
    
    async def hset(self, name: str, key: str, value: str) -> int:
        """Set field value in hash."""
        await self.ensure_connected()
        try:
            return await self._redis.hset(name, key, value)
        except Exception as e:
            logger.error(f"Redis HSET error for hash {name}, key {key}: {e}")
            return 0
    
    async def hgetall(self, name: str) -> Dict[str, str]:
        """Get all fields from hash."""
        await self.ensure_connected()
        try:
            return await self._redis.hgetall(name)
        except Exception as e:
            logger.error(f"Redis HGETALL error for hash {name}: {e}")
            return {}
    
    async def hdel(self, name: str, *keys: str) -> int:
        """Delete fields from hash."""
        await self.ensure_connected()
        try:
            return await self._redis.hdel(name, *keys)
        except Exception as e:
            logger.error(f"Redis HDEL error for hash {name}, keys {keys}: {e}")
            return 0
    
    async def lpush(self, name: str, *values: str) -> int:
        """Push values to left of list."""
        await self.ensure_connected()
        try:
            return await self._redis.lpush(name, *values)
        except Exception as e:
            logger.error(f"Redis LPUSH error for list {name}: {e}")
            return 0
    
    async def rpush(self, name: str, *values: str) -> int:
        """Push values to right of list."""
        await self.ensure_connected()
        try:
            return await self._redis.rpush(name, *values)
        except Exception as e:
            logger.error(f"Redis RPUSH error for list {name}: {e}")
            return 0
    
    async def lpop(self, name: str) -> Optional[str]:
        """Pop value from left of list."""
        await self.ensure_connected()
        try:
            return await self._redis.lpop(name)
        except Exception as e:
            logger.error(f"Redis LPOP error for list {name}: {e}")
            return None
    
    async def lrange(self, name: str, start: int, end: int) -> List[str]:
        """Get range of values from list."""
        await self.ensure_connected()
        try:
            return await self._redis.lrange(name, start, end)
        except Exception as e:
            logger.error(f"Redis LRANGE error for list {name}: {e}")
            return []
    
    async def sadd(self, name: str, *values: str) -> int:
        """Add members to set."""
        await self.ensure_connected()
        try:
            return await self._redis.sadd(name, *values)
        except Exception as e:
            logger.error(f"Redis SADD error for set {name}: {e}")
            return 0
    
    async def srem(self, name: str, *values: str) -> int:
        """Remove members from set."""
        await self.ensure_connected()
        try:
            return await self._redis.srem(name, *values)
        except Exception as e:
            logger.error(f"Redis SREM error for set {name}: {e}")
            return 0
    
    async def smembers(self, name: str) -> set:
        """Get all members from set."""
        await self.ensure_connected()
        try:
            return await self._redis.smembers(name)
        except Exception as e:
            logger.error(f"Redis SMEMBERS error for set {name}: {e}")
            return set()
    
    async def sismember(self, name: str, value: str) -> bool:
        """Check if value is member of set."""
        await self.ensure_connected()
        try:
            return bool(await self._redis.sismember(name, value))
        except Exception as e:
            logger.error(f"Redis SISMEMBER error for set {name}: {e}")
            return False
    
    async def zadd(self, name: str, mapping: Dict[str, float]) -> int:
        """Add members with scores to sorted set."""
        await self.ensure_connected()
        try:
            return await self._redis.zadd(name, mapping)
        except Exception as e:
            logger.error(f"Redis ZADD error for sorted set {name}: {e}")
            return 0
    
    async def zrange(
        self, 
        name: str, 
        start: int, 
        end: int, 
        withscores: bool = False
    ) -> List[Union[str, tuple]]:
        """Get range from sorted set."""
        await self.ensure_connected()
        try:
            return await self._redis.zrange(name, start, end, withscores=withscores)
        except Exception as e:
            logger.error(f"Redis ZRANGE error for sorted set {name}: {e}")
            return []
    
    async def zrem(self, name: str, *values: str) -> int:
        """Remove members from sorted set."""
        await self.ensure_connected()
        try:
            return await self._redis.zrem(name, *values)
        except Exception as e:
            logger.error(f"Redis ZREM error for sorted set {name}: {e}")
            return 0
    
    async def keys(self, pattern: str = "*") -> List[str]:
        """Get keys matching pattern."""
        await self.ensure_connected()
        try:
            return await self._redis.keys(pattern)
        except Exception as e:
            logger.error(f"Redis KEYS error for pattern {pattern}: {e}")
            return []
    
    async def flushdb(self) -> bool:
        """Clear current database."""
        await self.ensure_connected()
        try:
            return bool(await self._redis.flushdb())
        except Exception as e:
            logger.error(f"Redis FLUSHDB error: {e}")
            return False
    
    async def ping(self) -> bool:
        """Test Redis connection."""
        await self.ensure_connected()
        try:
            result = await self._redis.ping()
            return bool(result)
        except Exception as e:
            logger.error(f"Redis PING error: {e}")
            return False
    
    async def info(self) -> Dict[str, Any]:
        """Get Redis server information."""
        await self.ensure_connected()
        try:
            return await self._redis.info()
        except Exception as e:
            logger.error(f"Redis INFO error: {e}")
            return {}
    
    def get_json(self, data: Any) -> str:
        """Serialize data to JSON string."""
        return json.dumps(data, default=str)
    
    def parse_json(self, data: str) -> Any:
        """Parse JSON string to data."""
        try:
            return json.loads(data)
        except (json.JSONDecodeError, TypeError):
            return data
    
    @property
    def is_connected(self) -> bool:
        """Check if Redis is connected."""
        return self._is_connected


# Global Redis client instance
redis_client = RedisClient()