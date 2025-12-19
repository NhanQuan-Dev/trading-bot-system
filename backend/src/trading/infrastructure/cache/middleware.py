import time
import logging
from typing import Callable, Optional, Any
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from .cache_service import cache_service

logger = logging.getLogger(__name__)


class CacheMiddleware(BaseHTTPMiddleware):
    """Middleware for cache-related operations."""
    
    def __init__(self, app, cache_headers: bool = True):
        super().__init__(app)
        self.cache_headers = cache_headers
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and add cache-related functionality."""
        start_time = time.time()
        
        # Add cache service to request state
        request.state.cache = cache_service
        
        # Process request
        response = await call_next(request)
        
        # Add cache-related headers if enabled
        if self.cache_headers:
            self._add_cache_headers(request, response, start_time)
        
        return response
    
    def _add_cache_headers(self, request: Request, response: Response, start_time: float):
        """Add cache-related headers to response."""
        try:
            # Add cache status header
            cache_status = "MISS"  # Default to miss
            if hasattr(request.state, "cache_hit"):
                cache_status = "HIT" if request.state.cache_hit else "MISS"
            
            response.headers["X-Cache-Status"] = cache_status
            response.headers["X-Cache-Service"] = "Redis"
            
            # Add processing time
            processing_time = time.time() - start_time
            response.headers["X-Processing-Time"] = f"{processing_time:.3f}s"
            
        except Exception as e:
            logger.error(f"Error adding cache headers: {e}")


def cache_response(
    ttl: int = 300,
    key_prefix: str = "",
    use_query_params: bool = True,
    use_path: bool = True
):
    """Decorator for caching route responses."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # This is a simplified version - in production you'd want
            # to integrate with FastAPI's dependency injection system
            request = kwargs.get('request')
            if not request:
                # No request object, can't cache
                return await func(*args, **kwargs)
            
            # Generate cache key
            cache_key = _generate_cache_key(
                request, key_prefix, use_query_params, use_path
            )
            
            try:
                # Try to get from cache
                cached_data = await cache_service.redis_client.get(cache_key)
                if cached_data:
                    request.state.cache_hit = True
                    return cache_service.redis_client.parse_json(cached_data)
                
                # Execute function and cache result
                result = await func(*args, **kwargs)
                
                # Cache the result
                serialized_result = cache_service.redis_client.get_json(result)
                await cache_service.redis_client.set(cache_key, serialized_result, ex=ttl)
                
                request.state.cache_hit = False
                return result
                
            except Exception as e:
                logger.error(f"Error in cache decorator: {e}")
                # Fall back to executing function without cache
                return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def _generate_cache_key(
    request: Request,
    prefix: str,
    use_query_params: bool,
    use_path: bool
) -> str:
    """Generate cache key from request."""
    parts = []
    
    if prefix:
        parts.append(prefix)
    
    if use_path:
        parts.append(request.url.path)
    
    if use_query_params and request.query_params:
        query_string = str(request.query_params)
        parts.append(query_string)
    
    # Add user context if available
    if hasattr(request.state, "user_id"):
        parts.append(f"user:{request.state.user_id}")
    
    return ":".join(parts).replace("/", "_")