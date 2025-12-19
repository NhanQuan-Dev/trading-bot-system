"""
Latency measurement decorator

Usage:
    from shared.performance.profiling.latency_probe import measure_latency
    
    @measure_latency("api_call")
    async def fetch_data():
        ...
"""

import time
import functools
from typing import Callable, Optional, Dict
import asyncio


class LatencyStats:
    """Store and calculate latency statistics"""
    
    def __init__(self):
        self.measurements: Dict[str, list] = {}
    
    def record(self, name: str, duration: float) -> None:
        """Record a measurement"""
        if name not in self.measurements:
            self.measurements[name] = []
        self.measurements[name].append(duration)
    
    def get_stats(self, name: str) -> Optional[Dict]:
        """Get statistics for a measurement"""
        if name not in self.measurements or not self.measurements[name]:
            return None
        
        data = self.measurements[name]
        return {
            "count": len(data),
            "min": min(data),
            "max": max(data),
            "avg": sum(data) / len(data),
            "total": sum(data)
        }
    
    def get_all_stats(self) -> Dict:
        """Get all statistics"""
        return {name: self.get_stats(name) for name in self.measurements}
    
    def reset(self, name: Optional[str] = None) -> None:
        """Reset measurements"""
        if name:
            self.measurements[name] = []
        else:
            self.measurements.clear()
    
    def print_report(self) -> None:
        """Print formatted report"""
        print("\n" + "="*60)
        print("LATENCY REPORT")
        print("="*60)
        
        for name, stats in self.get_all_stats().items():
            if stats:
                print(f"\n{name}:")
                print(f"  Count: {stats['count']}")
                print(f"  Min:   {stats['min']*1000:.2f}ms")
                print(f"  Max:   {stats['max']*1000:.2f}ms")
                print(f"  Avg:   {stats['avg']*1000:.2f}ms")
                print(f"  Total: {stats['total']*1000:.2f}ms")
        
        print("="*60 + "\n")


# Global stats instance
_stats = LatencyStats()


def get_stats() -> LatencyStats:
    """Get global stats instance"""
    return _stats


def measure_latency(name: str, print_result: bool = False):
    """
    Decorator to measure function latency
    
    Args:
        name: Measurement name
        print_result: Print result after each call
    """
    def decorator(func: Callable):
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                start = time.perf_counter()
                try:
                    result = await func(*args, **kwargs)
                    return result
                finally:
                    duration = time.perf_counter() - start
                    _stats.record(name, duration)
                    if print_result:
                        print(f"[{name}] took {duration*1000:.2f}ms")
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                start = time.perf_counter()
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    duration = time.perf_counter() - start
                    _stats.record(name, duration)
                    if print_result:
                        print(f"[{name}] took {duration*1000:.2f}ms")
            return sync_wrapper
    return decorator


class LatencyProbe:
    """Context manager for manual latency measurement"""
    
    def __init__(self, name: str, print_result: bool = False):
        self.name = name
        self.print_result = print_result
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.perf_counter()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.perf_counter() - self.start_time
        _stats.record(self.name, duration)
        if self.print_result:
            print(f"[{self.name}] took {duration*1000:.2f}ms")


# Async context manager
class AsyncLatencyProbe:
    """Async context manager for latency measurement"""
    
    def __init__(self, name: str, print_result: bool = False):
        self.name = name
        self.print_result = print_result
        self.start_time = None
    
    async def __aenter__(self):
        self.start_time = time.perf_counter()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        duration = time.perf_counter() - self.start_time
        _stats.record(self.name, duration)
        if self.print_result:
            print(f"[{self.name}] took {duration*1000:.2f}ms")
