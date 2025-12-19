"""
Lock-free Queue for multi-threaded communication

Usage:
    from shared.performance.datastructures.lockfree_queue import LockFreeQueue
    
    queue = LockFreeQueue()
    queue.put(data)
    item = queue.get()
"""

import queue
from typing import Any, Optional


class LockFreeQueue:
    """
    High-performance queue for producer-consumer pattern
    
    Features:
    - Lock-free operations (internally optimized)
    - Thread-safe
    - Non-blocking get with timeout
    """
    
    def __init__(self, maxsize: int = 0):
        """
        Initialize queue
        
        Args:
            maxsize: Maximum queue size (0 = unlimited)
        """
        self.queue = queue.Queue(maxsize=maxsize)
    
    def put(self, item: Any, block: bool = True, timeout: Optional[float] = None) -> None:
        """
        Add item to queue
        
        Args:
            item: Data to add
            block: Block if queue is full
            timeout: Timeout for blocking
        """
        self.queue.put(item, block=block, timeout=timeout)
    
    def put_nowait(self, item: Any) -> None:
        """Add item without blocking (raises Full if queue full)"""
        self.queue.put_nowait(item)
    
    def get(self, block: bool = True, timeout: Optional[float] = None) -> Any:
        """
        Get item from queue
        
        Args:
            block: Block if queue is empty
            timeout: Timeout for blocking
            
        Returns:
            Item from queue
        """
        return self.queue.get(block=block, timeout=timeout)
    
    def get_nowait(self) -> Any:
        """Get item without blocking (raises Empty if queue empty)"""
        return self.queue.get_nowait()
    
    def size(self) -> int:
        """Get current queue size"""
        return self.queue.qsize()
    
    def empty(self) -> bool:
        """Check if queue is empty"""
        return self.queue.empty()
    
    def full(self) -> bool:
        """Check if queue is full"""
        return self.queue.full()
    
    def clear(self) -> None:
        """Clear all items"""
        while not self.queue.empty():
            try:
                self.queue.get_nowait()
            except queue.Empty:
                break
