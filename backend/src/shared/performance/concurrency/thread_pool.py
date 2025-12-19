"""
Thread Pool utilities

Usage:
    from shared.performance.concurrency.thread_pool import ThreadPool
    
    with ThreadPool(workers=4) as pool:
        results = pool.map(process_func, data_list)
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, List, Any, Optional, Iterator
import time


class ThreadPool:
    """
    Managed thread pool for concurrent operations
    
    Features:
    - Context manager support
    - Progress tracking
    - Error handling
    - Timeout support
    """
    
    def __init__(self, max_workers: Optional[int] = None):
        """
        Initialize thread pool
        
        Args:
            max_workers: Number of worker threads (None = CPU count * 5)
        """
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
    
    def submit(self, fn: Callable, *args, **kwargs):
        """
        Submit single task
        
        Args:
            fn: Function to execute
            *args, **kwargs: Function arguments
            
        Returns:
            Future object
        """
        return self.executor.submit(fn, *args, **kwargs)
    
    def map(
        self,
        fn: Callable,
        iterables: List[Any],
        timeout: Optional[float] = None,
        chunksize: int = 1
    ) -> Iterator[Any]:
        """
        Map function over iterables (parallel)
        
        Args:
            fn: Function to execute
            iterables: Input data
            timeout: Operation timeout
            chunksize: Items per thread
            
        Returns:
            Iterator of results
        """
        return self.executor.map(fn, iterables, timeout=timeout, chunksize=chunksize)
    
    def map_with_progress(
        self,
        fn: Callable,
        iterables: List[Any],
        timeout: Optional[float] = None
    ) -> List[Any]:
        """
        Map with progress tracking
        
        Args:
            fn: Function to execute
            iterables: Input data
            timeout: Operation timeout
            
        Returns:
            List of results
        """
        futures = [self.executor.submit(fn, item) for item in iterables]
        results = []
        
        for i, future in enumerate(as_completed(futures, timeout=timeout)):
            result = future.result()
            results.append(result)
            print(f"Progress: {i+1}/{len(futures)}", end='\r')
        
        print()  # New line after progress
        return results
    
    def shutdown(self, wait: bool = True):
        """
        Shutdown thread pool
        
        Args:
            wait: Wait for pending tasks to complete
        """
        self.executor.shutdown(wait=wait)
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown()


def run_concurrent(func: Callable, items: List[Any], max_workers: int = 4) -> List[Any]:
    """
    Quick utility to run function concurrently
    
    Args:
        func: Function to execute
        items: Input items
        max_workers: Number of workers
        
    Returns:
        List of results
    """
    with ThreadPool(max_workers=max_workers) as pool:
        return list(pool.map(func, items))
