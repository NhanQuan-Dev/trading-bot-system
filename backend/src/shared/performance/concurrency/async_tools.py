"""
Async/await utilities

Usage:
    from shared.performance.concurrency.async_tools import run_parallel, timeout_after
    
    results = await run_parallel([task1(), task2(), task3()])
"""

import asyncio
from typing import List, Any, Optional, Callable, Coroutine
import functools


async def run_parallel(tasks: List[Coroutine]) -> List[Any]:
    """
    Run multiple async tasks in parallel
    
    Args:
        tasks: List of coroutines
        
    Returns:
        List of results
    """
    return await asyncio.gather(*tasks)


async def run_parallel_with_errors(tasks: List[Coroutine]) -> List[Any]:
    """
    Run tasks in parallel, continue on errors
    
    Args:
        tasks: List of coroutines
        
    Returns:
        List of results (None for failed tasks)
    """
    return await asyncio.gather(*tasks, return_exceptions=True)


async def timeout_after(coro: Coroutine, timeout: float, default: Any = None) -> Any:
    """
    Run coroutine with timeout
    
    Args:
        coro: Coroutine to execute
        timeout: Timeout in seconds
        default: Default value on timeout
        
    Returns:
        Result or default value
    """
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        return default


async def retry_async(
    coro_func: Callable,
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,)
) -> Any:
    """
    Retry async function with exponential backoff
    
    Args:
        coro_func: Async function to retry
        max_attempts: Maximum retry attempts
        delay: Initial delay between retries
        backoff: Backoff multiplier
        exceptions: Exceptions to catch
        
    Returns:
        Function result
    """
    attempt = 0
    current_delay = delay
    
    while attempt < max_attempts:
        try:
            return await coro_func()
        except exceptions as e:
            attempt += 1
            if attempt >= max_attempts:
                raise
            
            await asyncio.sleep(current_delay)
            current_delay *= backoff


def async_cache(ttl: Optional[float] = None):
    """
    Decorator to cache async function results
    
    Args:
        ttl: Time-to-live in seconds (None = no expiry)
    """
    def decorator(func):
        cache = {}
        
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            key = str(args) + str(kwargs)
            
            if key in cache:
                result, timestamp = cache[key]
                if ttl is None or (asyncio.get_event_loop().time() - timestamp) < ttl:
                    return result
            
            result = await func(*args, **kwargs)
            cache[key] = (result, asyncio.get_event_loop().time())
            return result
        
        return wrapper
    return decorator


class AsyncRateLimiter:
    """
    Rate limiter for async operations
    
    Usage:
        limiter = AsyncRateLimiter(max_calls=10, period=1.0)
        
        async with limiter:
            await api_call()
    """
    
    def __init__(self, max_calls: int, period: float):
        """
        Initialize rate limiter
        
        Args:
            max_calls: Maximum calls per period
            period: Time period in seconds
        """
        self.max_calls = max_calls
        self.period = period
        self.calls = []
        self.lock = asyncio.Lock()
    
    async def __aenter__(self):
        async with self.lock:
            now = asyncio.get_event_loop().time()
            
            # Remove old calls
            self.calls = [t for t in self.calls if now - t < self.period]
            
            # Wait if limit reached
            if len(self.calls) >= self.max_calls:
                sleep_time = self.period - (now - self.calls[0])
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                self.calls = self.calls[1:]
            
            self.calls.append(now)
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
