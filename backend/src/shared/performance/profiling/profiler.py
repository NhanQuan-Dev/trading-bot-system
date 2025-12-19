"""
Code profiling utilities

Usage:
    from shared.performance.profiling.profiler import profile_function
    
    @profile_function
    def slow_function():
        ...
"""

import cProfile
import pstats
import io
import functools
from typing import Callable, Optional
import time


def profile_function(func: Callable):
    """
    Decorator to profile function execution
    
    Prints detailed stats after function completes
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        profiler = cProfile.Profile()
        profiler.enable()
        
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            profiler.disable()
            
            # Print stats
            s = io.StringIO()
            ps = pstats.Stats(profiler, stream=s).sort_stats('cumulative')
            ps.print_stats(20)  # Top 20 functions
            
            print(f"\n{'='*60}")
            print(f"PROFILE: {func.__name__}")
            print('='*60)
            print(s.getvalue())
    
    return wrapper


class MemoryTracker:
    """
    Track memory usage
    
    Usage:
        tracker = MemoryTracker()
        tracker.start()
        # ... code to profile
        tracker.stop()
        tracker.print_report()
    """
    
    def __init__(self):
        try:
            from pympler import tracker
            self.tracker = tracker.SummaryTracker()
            self.available = True
        except ImportError:
            self.tracker = None
            self.available = False
            print("Warning: pympler not installed. Memory tracking disabled.")
    
    def start(self) -> None:
        """Start tracking"""
        if self.available:
            self.tracker.print_diff()
    
    def stop(self) -> None:
        """Stop tracking and print diff"""
        if self.available:
            self.tracker.print_diff()
    
    def print_report(self) -> None:
        """Print memory report"""
        if self.available:
            self.tracker.print_diff()


class FunctionTimer:
    """
    Simple function timer
    
    Usage:
        timer = FunctionTimer()
        timer.start()
        # ... code
        elapsed = timer.stop()
    """
    
    def __init__(self):
        self.start_time = None
        self.elapsed = None
    
    def start(self) -> None:
        """Start timer"""
        self.start_time = time.perf_counter()
    
    def stop(self) -> float:
        """Stop timer and return elapsed time"""
        if self.start_time is None:
            raise RuntimeError("Timer not started")
        
        self.elapsed = time.perf_counter() - self.start_time
        return self.elapsed
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        print(f"Elapsed: {self.elapsed*1000:.2f}ms")


def benchmark(func: Callable, iterations: int = 1000, warmup: int = 100):
    """
    Benchmark function performance
    
    Args:
        func: Function to benchmark
        iterations: Number of test iterations
        warmup: Number of warmup iterations
    """
    # Warmup
    for _ in range(warmup):
        func()
    
    # Benchmark
    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        func()
        times.append(time.perf_counter() - start)
    
    # Stats
    avg = sum(times) / len(times)
    min_time = min(times)
    max_time = max(times)
    
    print(f"\n{'='*60}")
    print(f"BENCHMARK: {func.__name__}")
    print('='*60)
    print(f"Iterations: {iterations}")
    print(f"Avg:        {avg*1000:.4f}ms")
    print(f"Min:        {min_time*1000:.4f}ms")
    print(f"Max:        {max_time*1000:.4f}ms")
    print(f"Total:      {sum(times)*1000:.4f}ms")
    print('='*60 + '\n')
