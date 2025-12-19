from src.domain.entities.position import Position
from src.shared.utils.formatter import format_number

class PositionView:
    def __init__(self, position: Position):
        self.position = position

    def display(self) -> str:
        position_side = self.position.position_side
        qty = format_number(self.position.position_amt)
        entry_price = format_number(self.position.entry_price)
        unrealized_pnl = format_number(self.position.unrealized_pnl)

        return (
            f"Position: {self.position.symbol} | "
            f"Side: {position_side} | "
            f"Qty: {qty} | "
            f"Entry Price: {entry_price} | "
            f"Unrealized PnL: {unrealized_pnl}"
        )