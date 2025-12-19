import logging
from typing import Optional, Dict, List, Any, TypeVar, Generic, Type
from datetime import datetime, timedelta
import hashlib
import json

from .base_cache import BaseCache
from .cache_service import cache_service

logger = logging.getLogger(__name__)

T = TypeVar('T')


class CachedRepository(Generic[T]):
    """Wrapper for repositories to add caching functionality."""
    
    def __init__(
        self, 
        repository: Any,
        cache: Optional[BaseCache] = None,
        default_ttl: int = 300,
        cache_prefix: str = ""
    ):
        self.repository = repository
        self.cache = cache or cache_service.redis_client
        self.default_ttl = default_ttl
        self.cache_prefix = cache_prefix
    
    def _make_cache_key(self, method: str, *args, **kwargs) -> str:
        """Generate cache key for method call."""
        # Create a unique key based on method name and arguments
        key_parts = [self.cache_prefix, method] if self.cache_prefix else [method]
        
        # Add positional arguments
        for arg in args:
            if hasattr(arg, 'id'):
                key_parts.append(str(arg.id))
            elif isinstance(arg, (str, int, float)):
                key_parts.append(str(arg))
            else:
                # For complex objects, use hash
                arg_hash = hashlib.md5(str(arg).encode()).hexdigest()[:8]
                key_parts.append(arg_hash)
        
        # Add keyword arguments
        if kwargs:
            sorted_kwargs = sorted(kwargs.items())
            kwargs_str = json.dumps(sorted_kwargs, default=str, sort_keys=True)
            kwargs_hash = hashlib.md5(kwargs_str.encode()).hexdigest()[:8]
            key_parts.append(kwargs_hash)
        
        return ":".join(key_parts)
    
    async def cached_call(
        self, 
        method_name: str, 
        ttl: Optional[int] = None,
        cache_key_override: Optional[str] = None,
        force_refresh: bool = False,
        *args, 
        **kwargs
    ) -> Any:
        """Execute repository method with caching."""
        ttl = ttl or self.default_ttl
        cache_key = cache_key_override or self._make_cache_key(method_name, *args, **kwargs)
        
        # Check cache first (unless force refresh)
        if not force_refresh:
            try:
                if hasattr(self.cache, 'get'):
                    cached_result = await self.cache.get(cache_key)
                else:
                    cached_result = await cache_service.redis_client.get(cache_key)
                
                if cached_result is not None:
                    logger.debug(f"Cache HIT for {cache_key}")
                    return self._deserialize_result(cached_result)
            except Exception as e:
                logger.error(f"Cache GET error for {cache_key}: {e}")
        
        # Execute repository method
        try:
            method = getattr(self.repository, method_name)
            result = await method(*args, **kwargs)
            
            # Cache the result
            if result is not None:
                try:
                    serialized_result = self._serialize_result(result)
                    if hasattr(self.cache, 'set'):
                        await self.cache.set(cache_key, serialized_result, ttl)
                    else:
                        await cache_service.redis_client.set(cache_key, serialized_result, ex=ttl)
                    
                    logger.debug(f"Cache SET for {cache_key}")
                except Exception as e:
                    logger.error(f"Cache SET error for {cache_key}: {e}")
            
            return result
            
        except Exception as e:
            logger.error(f"Repository method {method_name} failed: {e}")
            raise
    
    def _serialize_result(self, result: Any) -> str:
        """Serialize result for caching."""
        if hasattr(result, 'dict'):
            # Pydantic model
            return json.dumps(result.dict(), default=str)
        elif hasattr(result, '__dict__'):
            # Object with attributes
            return json.dumps(result.__dict__, default=str)
        elif isinstance(result, (list, dict)):
            return json.dumps(result, default=str)
        else:
            return str(result)
    
    def _deserialize_result(self, cached_data: str) -> Any:
        """Deserialize cached result."""
        try:
            return json.loads(cached_data)
        except (json.JSONDecodeError, TypeError):
            return cached_data
    
    async def invalidate_cache(self, pattern: str = "*"):
        """Invalidate cache entries matching pattern."""
        try:
            if self.cache_prefix:
                pattern = f"{self.cache_prefix}:{pattern}"
            
            if hasattr(self.cache, 'clear_prefix'):
                return await self.cache.clear_prefix(pattern)
            else:
                keys = await cache_service.redis_client.keys(pattern)
                if keys:
                    return await cache_service.redis_client.delete(*keys)
                return 0
        except Exception as e:
            logger.error(f"Error invalidating cache: {e}")
            return 0
    
    async def get_by_id_cached(self, id: Any, ttl: int = 600) -> Optional[T]:
        """Get entity by ID with caching."""
        return await self.cached_call("get_by_id", ttl=ttl, id=id)
    
    async def find_cached(
        self, 
        filters: Dict[str, Any], 
        ttl: int = 300
    ) -> List[T]:
        """Find entities with caching."""
        return await self.cached_call("find", ttl=ttl, **filters)
    
    async def get_all_cached(self, ttl: int = 600) -> List[T]:
        """Get all entities with caching."""
        return await self.cached_call("get_all", ttl=ttl)
    
    # Delegate attribute access to wrapped repository
    def __getattr__(self, name):
        return getattr(self.repository, name)


class CacheInvalidationMixin:
    """Mixin for repositories to handle cache invalidation."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cache_prefix = getattr(self, 'cache_prefix', '')
    
    async def _invalidate_cache_after_write(self, entity_id: Any = None):
        """Invalidate relevant cache entries after write operations."""
        try:
            patterns = [f"{self._cache_prefix}:*"]
            
            if entity_id:
                patterns.extend([
                    f"{self._cache_prefix}:get_by_id:*{entity_id}*",
                    f"{self._cache_prefix}:find:*",
                    f"{self._cache_prefix}:get_all:*"
                ])
            
            for pattern in patterns:
                keys = await cache_service.redis_client.keys(pattern)
                if keys:
                    await cache_service.redis_client.delete(*keys)
                    logger.debug(f"Invalidated {len(keys)} cache entries for pattern {pattern}")
                    
        except Exception as e:
            logger.error(f"Error invalidating cache: {e}")
    
    async def create_with_cache_invalidation(self, entity: T) -> T:
        """Create entity and invalidate related cache."""
        result = await super().create(entity)
        await self._invalidate_cache_after_write(getattr(result, 'id', None))
        return result
    
    async def update_with_cache_invalidation(self, entity: T) -> T:
        """Update entity and invalidate related cache."""
        result = await super().update(entity)
        await self._invalidate_cache_after_write(getattr(result, 'id', None))
        return result
    
    async def delete_with_cache_invalidation(self, id: Any) -> bool:
        """Delete entity and invalidate related cache."""
        result = await super().delete(id)
        await self._invalidate_cache_after_write(id)
        return result


def cached_repository(
    cache_prefix: str = "",
    default_ttl: int = 300,
    cache_instance: Optional[BaseCache] = None
):
    """Decorator to wrap repository with caching functionality."""
    def decorator(repository_class):
        class CachedRepositoryWrapper(repository_class, CacheInvalidationMixin):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.cache_prefix = cache_prefix
                self._cached_repo = CachedRepository(
                    repository=self,
                    cache=cache_instance,
                    default_ttl=default_ttl,
                    cache_prefix=cache_prefix
                )
            
            async def get_by_id(self, id: Any, use_cache: bool = True, ttl: int = None):
                if use_cache:
                    return await self._cached_repo.get_by_id_cached(id, ttl or default_ttl)
                return await super().get_by_id(id)
            
            async def find(self, use_cache: bool = True, ttl: int = None, **filters):
                if use_cache:
                    return await self._cached_repo.find_cached(filters, ttl or default_ttl)
                return await super().find(**filters)
            
            async def get_all(self, use_cache: bool = True, ttl: int = None):
                if use_cache:
                    return await self._cached_repo.get_all_cached(ttl or default_ttl)
                return await super().get_all()
            
            async def create(self, entity: T) -> T:
                return await self.create_with_cache_invalidation(entity)
            
            async def update(self, entity: T) -> T:
                return await self.update_with_cache_invalidation(entity)
            
            async def delete(self, id: Any) -> bool:
                return await self.delete_with_cache_invalidation(id)
            
            async def invalidate_cache(self, pattern: str = "*"):
                return await self._cached_repo.invalidate_cache(pattern)
        
        return CachedRepositoryWrapper
    
    return decorator