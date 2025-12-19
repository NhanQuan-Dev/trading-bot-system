import asyncio
import logging
from typing import Optional, Dict, Any
from fastapi import FastAPI

from .redis_client import redis_client
from .market_data_cache import market_data_cache
from .user_session_cache import user_session_cache
from .price_cache import price_cache

logger = logging.getLogger(__name__)


class CacheService:
    """Service for managing all cache operations."""
    
    def __init__(self):
        self.redis_client = redis_client
        self.market_data = market_data_cache
        self.user_session = user_session_cache
        self.price = price_cache
        self.is_running = False
    
    async def start(self):
        """Start cache service and establish connections."""
        if self.is_running:
            return
        
        try:
            logger.info("Starting cache service...")
            
            # Connect to Redis
            await self.redis_client.connect()
            logger.info("Redis connection established")
            
            # Test cache operations
            await self._test_cache_operations()
            
            self.is_running = True
            logger.info("Cache service started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start cache service: {e}")
            raise
    
    async def stop(self):
        """Stop cache service and close connections."""
        if not self.is_running:
            return
        
        try:
            logger.info("Stopping cache service...")
            
            # Disconnect from Redis
            await self.redis_client.disconnect()
            
            self.is_running = False
            logger.info("Cache service stopped successfully")
            
        except Exception as e:
            logger.error(f"Error stopping cache service: {e}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Check cache service health."""
        try:
            # Test Redis connection
            redis_healthy = await self.redis_client.ping()
            
            # Get Redis info
            redis_info = await self.redis_client.info() if redis_healthy else {}
            
            # Get cache statistics
            stats = {
                "market_data": await self.market_data.get_stats(),
                "user_session": await self.user_session.get_stats(),
                "price": await self.price.get_stats()
            }
            
            return {
                "status": "healthy" if redis_healthy else "unhealthy",
                "redis_connected": redis_healthy,
                "redis_info": {
                    "version": redis_info.get("redis_version", "unknown"),
                    "used_memory": redis_info.get("used_memory_human", "unknown"),
                    "connected_clients": redis_info.get("connected_clients", 0),
                    "uptime": redis_info.get("uptime_in_seconds", 0)
                },
                "cache_stats": stats,
                "is_running": self.is_running
            }
        except Exception as e:
            logger.error(f"Error checking cache health: {e}")
            return {
                "status": "error",
                "error": str(e),
                "is_running": self.is_running
            }
    
    async def _test_cache_operations(self):
        """Test basic cache operations."""
        test_key = "test:connection"
        test_value = "cache_test_value"
        
        # Test set/get
        success = await self.redis_client.set(test_key, test_value, ex=60)
        if not success:
            raise Exception("Failed to set test cache value")
        
        retrieved = await self.redis_client.get(test_key)
        if retrieved != test_value:
            raise Exception("Failed to retrieve test cache value")
        
        # Clean up
        await self.redis_client.delete(test_key)
        
        logger.info("Cache operations test passed")
    
    async def clear_all_cache(self) -> Dict[str, int]:
        """Clear all cached data (use with caution)."""
        try:
            results = {
                "market_data": await self.market_data.clear_prefix(),
                "user_session": await self.user_session.clear_prefix(),
                "price": await self.price.clear_prefix()
            }
            
            logger.warning("All cache data cleared")
            return results
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return {"error": str(e)}
    
    async def cleanup_expired_data(self) -> Dict[str, Any]:
        """Clean up expired data across all caches."""
        try:
            results = {
                "market_data": await self.market_data.cleanup_expired_data(),
                "user_sessions": await self.user_session.cleanup_expired_sessions(),
                "price_data": await self.price.cleanup_old_data()
            }
            
            logger.info(f"Cache cleanup completed: {results}")
            return results
        except Exception as e:
            logger.error(f"Error during cache cleanup: {e}")
            return {"error": str(e)}
    
    async def get_cache_summary(self) -> Dict[str, Any]:
        """Get summary of all cache data."""
        try:
            # Get Redis memory info
            redis_info = await self.redis_client.info()
            
            # Get cache-specific stats
            market_stats = await self.market_data.get_stats()
            session_stats = await self.user_session.get_stats()
            price_stats = await self.price.get_stats()
            
            # Get all symbols with cached data
            cached_symbols = await self.market_data.get_all_symbols()
            
            return {
                "redis_memory": redis_info.get("used_memory_human", "unknown"),
                "total_keys": (
                    market_stats.get("total_keys", 0) +
                    session_stats.get("total_keys", 0) +
                    price_stats.get("total_keys", 0)
                ),
                "cache_breakdown": {
                    "market_data": market_stats,
                    "user_sessions": session_stats,
                    "price_data": price_stats
                },
                "cached_symbols": cached_symbols,
                "symbol_count": len(cached_symbols)
            }
        except Exception as e:
            logger.error(f"Error getting cache summary: {e}")
            return {"error": str(e)}
    
    def get_market_cache(self):
        """Get market data cache instance."""
        return self.market_data
    
    def get_session_cache(self):
        """Get user session cache instance."""
        return self.user_session
    
    def get_price_cache(self):
        """Get price cache instance."""
        return self.price


# Global cache service instance
cache_service = CacheService()


# FastAPI lifespan events
async def cache_startup():
    """Cache service startup event."""
    await cache_service.start()


async def cache_shutdown():
    """Cache service shutdown event."""
    await cache_service.stop()