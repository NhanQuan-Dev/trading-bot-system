from typing import List, Tuple

class OrderBook:
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.bids: List[Tuple[float, float]] = []  # List of (price, quantity) for bids
        self.asks: List[Tuple[float, float]] = []  # List of (price, quantity) for asks

    def update_bids(self, bids: List[Tuple[float, float]]):
        self.bids = bids

    def update_asks(self, asks: List[Tuple[float, float]]):
        self.asks = asks

    def get_best_bid(self) -> Tuple[float, float]:
        return self.bids[0] if self.bids else (0.0, 0.0)

    def get_best_ask(self) -> Tuple[float, float]:
        return self.asks[0] if self.asks else (0.0, 0.0)

    def __repr__(self):
        return f"OrderBook(symbol={self.symbol}, bids={self.bids}, asks={self.asks})"