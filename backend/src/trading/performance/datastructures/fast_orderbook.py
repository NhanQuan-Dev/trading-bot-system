"""
Optimized OrderBook data structure

Usage:
    from shared.performance.datastructures.fast_orderbook import FastOrderBook
    
    ob = FastOrderBook()
    ob.update_bid(50000.0, 1.5)
    ob.update_ask(50100.0, 2.0)
    best_bid = ob.get_best_bid()
"""

from typing import Dict, List, Tuple, Optional
from sortedcontainers import SortedDict


class FastOrderBook:
    """
    High-performance order book using SortedDict
    
    Features:
    - O(log n) updates
    - O(1) best bid/ask access
    - Efficient depth queries
    - Memory-efficient
    """
    
    def __init__(self):
        """Initialize order book"""
        self.bids = SortedDict()  # price -> quantity (descending)
        self.asks = SortedDict()  # price -> quantity (ascending)
    
    def update_bid(self, price: float, quantity: float) -> None:
        """
        Update bid level
        
        Args:
            price: Bid price
            quantity: Bid quantity (0 to remove)
        """
        if quantity <= 0 and price in self.bids:
            del self.bids[price]
        elif quantity > 0:
            self.bids[price] = quantity
    
    def update_ask(self, price: float, quantity: float) -> None:
        """
        Update ask level
        
        Args:
            price: Ask price
            quantity: Ask quantity (0 to remove)
        """
        if quantity <= 0 and price in self.asks:
            del self.asks[price]
        elif quantity > 0:
            self.asks[price] = quantity
    
    def get_best_bid(self) -> Optional[Tuple[float, float]]:
        """
        Get best bid (highest price)
        
        Returns:
            (price, quantity) or None if no bids
        """
        if not self.bids:
            return None
        price = self.bids.keys()[-1]  # Highest price
        return (price, self.bids[price])
    
    def get_best_ask(self) -> Optional[Tuple[float, float]]:
        """
        Get best ask (lowest price)
        
        Returns:
            (price, quantity) or None if no asks
        """
        if not self.asks:
            return None
        price = self.asks.keys()[0]  # Lowest price
        return (price, self.asks[price])
    
    def get_spread(self) -> Optional[float]:
        """
        Get bid-ask spread
        
        Returns:
            Spread or None if incomplete book
        """
        best_bid = self.get_best_bid()
        best_ask = self.get_best_ask()
        
        if best_bid and best_ask:
            return best_ask[0] - best_bid[0]
        return None
    
    def get_depth(self, levels: int = 10) -> Dict[str, List[Tuple[float, float]]]:
        """
        Get order book depth
        
        Args:
            levels: Number of levels to return
            
        Returns:
            Dict with 'bids' and 'asks' lists
        """
        bids = [(price, qty) for price, qty in reversed(list(self.bids.items())[:levels])]
        asks = [(price, qty) for price, qty in list(self.asks.items())[:levels]]
        
        return {
            "bids": bids,
            "asks": asks
        }
    
    def clear(self) -> None:
        """Clear all orders"""
        self.bids.clear()
        self.asks.clear()
    
    def snapshot(self) -> Dict:
        """Get full orderbook snapshot"""
        return {
            "bids": list(self.bids.items()),
            "asks": list(self.asks.items())
        }
