"""Trade domain model."""
from dataclasses import dataclass
from datetime import datetime as dt
from decimal import Decimal
import uuid
from typing import Optional

from ..order import OrderSide

@dataclass
class Trade:
    """Trade entity representing a filled execution."""
    id: uuid.UUID
    order_id: uuid.UUID
    bot_id: Optional[uuid.UUID]
    user_id: uuid.UUID
    symbol: str
    side: OrderSide
    price: Decimal
    quantity: Decimal
    commission: Decimal
    commission_asset: str
    realized_pnl: Decimal
    executed_at: dt
    
    # Metadata
    exchange_trade_id: Optional[str] = None
    
    @property
    def cost(self) -> Decimal:
        """Calculate trade cost (price * quantity)."""
        return self.price * self.quantity
    
    @property
    def value(self) -> Decimal:
        """Calculate trade value (price * quantity)."""
        return self.cost

    @classmethod
    def create(
        cls,
        order_id: uuid.UUID,
        user_id: uuid.UUID,
        symbol: str,
        side: OrderSide,
        price: Decimal,
        quantity: Decimal,
        commission: Decimal = Decimal("0"),
        commission_asset: str = "USDT",
        realized_pnl: Decimal = Decimal("0"),
        bot_id: Optional[uuid.UUID] = None,
        exchange_trade_id: Optional[str] = None,
        executed_at: Optional[dt] = None
    ) -> "Trade":
        """Create a new trade."""
        return cls(
            id=uuid.uuid4(),
            order_id=order_id,
            bot_id=bot_id,
            user_id=user_id,
            symbol=symbol,
            side=side,
            price=price,
            quantity=quantity,
            commission=commission,
            commission_asset=commission_asset,
            realized_pnl=realized_pnl,
            executed_at=executed_at or dt.utcnow(),
            exchange_trade_id=exchange_trade_id
        )
