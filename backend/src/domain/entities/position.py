from dataclasses import dataclass
from typing import Optional

@dataclass
class Position:
    symbol: str
    position_side: str
    position_amt: float
    entry_price: float
    leverage: Optional[int] = None
    unrealized_pnl: float = 0.0
    margin_type: str = "cross"

    def calculate_unrealized_pnl(self, current_price: float) -> float:
        """Calculate unrealized profit and loss based on the current market price."""
        if self.position_side == "LONG":
            return (current_price - self.entry_price) * self.position_amt
        elif self.position_side == "SHORT":
            return (self.entry_price - current_price) * self.position_amt
        return 0.0

    def __post_init__(self):
        if self.position_amt == 0:
            raise ValueError("Position amount cannot be zero.")
        if self.position_side not in ["LONG", "SHORT"]:
            raise ValueError("Position side must be either 'LONG' or 'SHORT'.")