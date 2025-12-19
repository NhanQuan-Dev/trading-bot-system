"""
Ring Buffer (Circular Buffer) for time-series data

Usage:
    from shared.performance.datastructures.ring_buffer import RingBuffer
    
    buffer = RingBuffer(capacity=1000)
    buffer.append(tick_data)
    latest = buffer.get_latest(10)
"""

from typing import Any, List, Optional
from collections import deque


class RingBuffer:
    """
    Fixed-size circular buffer optimized for time-series data
    
    Features:
    - O(1) append
    - O(1) access to latest N items
    - Memory-efficient (fixed size)
    - Thread-safe with lock (optional)
    """
    
    def __init__(self, capacity: int, thread_safe: bool = False):
        """
        Initialize ring buffer
        
        Args:
            capacity: Maximum number of items
            thread_safe: Enable thread-safety with lock
        """
        self.capacity = capacity
        self.buffer = deque(maxlen=capacity)
        self.thread_safe = thread_safe
        
        if thread_safe:
            from threading import Lock
            self.lock = Lock()
        else:
            self.lock = None
    
    def append(self, item: Any) -> None:
        """
        Add item to buffer (overwrites oldest if full)
        
        Args:
            item: Data item to add
        """
        if self.thread_safe:
            with self.lock:
                self.buffer.append(item)
        else:
            self.buffer.append(item)
    
    def get_latest(self, n: int) -> List[Any]:
        """
        Get latest N items
        
        Args:
            n: Number of items to retrieve
            
        Returns:
            List of latest N items (or all if less than N)
        """
        if self.thread_safe:
            with self.lock:
                return list(self.buffer)[-n:]
        else:
            return list(self.buffer)[-n:]
    
    def get_all(self) -> List[Any]:
        """Get all items in buffer"""
        if self.thread_safe:
            with self.lock:
                return list(self.buffer)
        else:
            return list(self.buffer)
    
    def clear(self) -> None:
        """Clear all items"""
        if self.thread_safe:
            with self.lock:
                self.buffer.clear()
        else:
            self.buffer.clear()
    
    def __len__(self) -> int:
        """Get current size"""
        return len(self.buffer)
    
    def is_full(self) -> bool:
        """Check if buffer is at capacity"""
        return len(self.buffer) == self.capacity
    
    def is_empty(self) -> bool:
        """Check if buffer is empty"""
        return len(self.buffer) == 0
