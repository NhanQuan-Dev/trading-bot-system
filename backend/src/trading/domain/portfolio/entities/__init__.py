"""Portfolio domain - Entities."""
from decimal import Decimal
from typing import Optional
from datetime import datetime, timezone
import uuid

from ..value_objects import PositionSide, MarginMode, Leverage, PnL, PositionRisk


class Position:
    """Position entity representing an open trading position."""
    
    def __init__(
        self,
        id: uuid.UUID,
        user_id: uuid.UUID,
        symbol: str,
        side: PositionSide,
        entry_price: Decimal,
        quantity: Decimal,
        leverage: Leverage,
        margin_mode: MarginMode,
        bot_id: Optional[uuid.UUID] = None,
        stop_loss: Optional[Decimal] = None,
        take_profit: Optional[Decimal] = None,
    ):
        self.id = id
        self.user_id = user_id
        self.symbol = symbol
        self.side = side
        self.entry_price = entry_price
        self.quantity = quantity
        self.leverage = leverage
        self.margin_mode = margin_mode
        self.bot_id = bot_id
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        
        self.mark_price = entry_price
        self.liquidation_price: Optional[Decimal] = None
        self.pnl = PnL(realized=Decimal("0"), unrealized=Decimal("0"))
        
        self.opened_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
        
        # Calculate initial values
        self._calculate_liquidation_price()
        self._update_unrealized_pnl()
    
    @property
    def margin_used(self) -> Decimal:
        """Calculate margin used for this position."""
        position_value = self.quantity * self.entry_price
        return position_value / self.leverage.value
    
    @property
    def position_value(self) -> Decimal:
        """Calculate current position value."""
        return self.quantity * self.mark_price
    
    def update_mark_price(self, new_price: Decimal) -> None:
        """Update mark price and recalculate metrics."""
        if new_price <= 0:
            raise ValueError(f"Mark price must be positive: {new_price}")
        
        self.mark_price = new_price
        self._update_unrealized_pnl()
        self.updated_at = datetime.now(timezone.utc)
    
    def _update_unrealized_pnl(self) -> None:
        """Calculate and update unrealized P&L."""
        price_diff = self.mark_price - self.entry_price
        
        if self.side == PositionSide.SHORT:
            price_diff = -price_diff
        
        unrealized = price_diff * self.quantity
        self.pnl = self.pnl.update_unrealized(unrealized)
    
    def _calculate_liquidation_price(self) -> None:
        """Calculate liquidation price based on leverage and margin mode."""
        if self.margin_mode == MarginMode.ISOLATED:
            # Simplified liquidation calculation for isolated margin
            # Liquidation happens when position loses 100% of margin
            maintenance_margin_rate = Decimal("0.01")  # 1%
            
            if self.side == PositionSide.LONG:
                # Long: liq_price = entry * (1 - 1/leverage + maintenance)
                self.liquidation_price = self.entry_price * (
                    1 - Decimal("1") / self.leverage.value + maintenance_margin_rate
                )
            else:
                # Short: liq_price = entry * (1 + 1/leverage - maintenance)
                self.liquidation_price = self.entry_price * (
                    1 + Decimal("1") / self.leverage.value - maintenance_margin_rate
                )
        else:
            # Cross margin liquidation depends on total account equity
            self.liquidation_price = None
    
    def update_stop_loss(self, price: Decimal) -> None:
        """Update stop loss price."""
        self._validate_stop_loss(price)
        self.stop_loss = price
        self.updated_at = datetime.now(timezone.utc)
    
    def update_take_profit(self, price: Decimal) -> None:
        """Update take profit price."""
        self._validate_take_profit(price)
        self.take_profit = price
        self.updated_at = datetime.now(timezone.utc)
    
    def _validate_stop_loss(self, price: Decimal) -> None:
        """Validate stop loss price."""
        if price <= 0:
            raise ValueError(f"Stop loss must be positive: {price}")
        
        if self.side == PositionSide.LONG and price >= self.entry_price:
            raise ValueError(f"Long stop loss must be below entry: {price} >= {self.entry_price}")
        
        if self.side == PositionSide.SHORT and price <= self.entry_price:
            raise ValueError(f"Short stop loss must be above entry: {price} <= {self.entry_price}")
    
    def _validate_take_profit(self, price: Decimal) -> None:
        """Validate take profit price."""
        if price <= 0:
            raise ValueError(f"Take profit must be positive: {price}")
        
        if self.side == PositionSide.LONG and price <= self.entry_price:
            raise ValueError(f"Long take profit must be above entry: {price} <= {self.entry_price}")
        
        if self.side == PositionSide.SHORT and price >= self.entry_price:
            raise ValueError(f"Short take profit must be below entry: {price} >= {self.entry_price}")
    
    def should_trigger_stop_loss(self) -> bool:
        """Check if stop loss should be triggered."""
        if self.stop_loss is None:
            return False
        
        if self.side == PositionSide.LONG:
            return self.mark_price <= self.stop_loss
        else:
            return self.mark_price >= self.stop_loss
    
    def should_trigger_take_profit(self) -> bool:
        """Check if take profit should be triggered."""
        if self.take_profit is None:
            return False
        
        if self.side == PositionSide.LONG:
            return self.mark_price >= self.take_profit
        else:
            return self.mark_price <= self.take_profit
    
    def should_liquidate(self) -> bool:
        """Check if position should be liquidated."""
        if self.liquidation_price is None:
            return False
        
        if self.side == PositionSide.LONG:
            return self.mark_price <= self.liquidation_price
        else:
            return self.mark_price >= self.liquidation_price
    
    def get_risk_metrics(self) -> PositionRisk:
        """Get current risk metrics."""
        margin_ratio = abs(self.pnl.unrealized) / self.margin_used if self.margin_used > 0 else Decimal("0")
        roe = self.pnl.calculate_roe(self.margin_used)
        
        return PositionRisk(
            liquidation_price=self.liquidation_price,
            margin_ratio=margin_ratio,
            unrealized_pnl=self.pnl.unrealized,
            roe=roe
        )
    
    def close(self, close_price: Decimal) -> Decimal:
        """Close position and calculate realized P&L."""
        if close_price <= 0:
            raise ValueError(f"Close price must be positive: {close_price}")
        
        # Update to final price
        self.update_mark_price(close_price)
        
        # Realize P&L
        realized_pnl = self.pnl.unrealized
        self.pnl = self.pnl.realize()
        
        return realized_pnl
    
    def __repr__(self) -> str:
        return (
            f"Position(id={self.id}, symbol={self.symbol}, side={self.side}, "
            f"quantity={self.quantity}, entry={self.entry_price}, "
            f"pnl={self.pnl.total})"
        )


class Balance:
    """Balance entity representing asset balance with free and locked amounts."""
    
    def __init__(self, user_id: uuid.UUID, asset: str, free: Decimal, locked: Decimal):
        self.user_id = user_id
        self.asset = asset
        self.free = free
        self.locked = locked
        self.updated_at = datetime.now(timezone.utc)
    
    @property
    def total(self) -> Decimal:
        """Total balance."""
        return self.free + self.locked
    
    def add_free(self, amount: Decimal) -> None:
        """Add to free balance."""
        if amount <= 0:
            raise ValueError(f"Amount must be positive: {amount}")
        self.free += amount
        self.updated_at = datetime.now(timezone.utc)
    
    def subtract_free(self, amount: Decimal) -> None:
        """Subtract from free balance."""
        if amount <= 0:
            raise ValueError(f"Amount must be positive: {amount}")
        if self.free < amount:
            raise ValueError(f"Insufficient free balance: {self.free} < {amount}")
        self.free -= amount
        self.updated_at = datetime.now(timezone.utc)
    
    def lock(self, amount: Decimal) -> None:
        """Lock amount (move from free to locked)."""
        if amount <= 0:
            raise ValueError(f"Amount must be positive: {amount}")
        if self.free < amount:
            raise ValueError(f"Insufficient free balance to lock: {self.free} < {amount}")
        self.free -= amount
        self.locked += amount
        self.updated_at = datetime.now(timezone.utc)
    
    def unlock(self, amount: Decimal) -> None:
        """Unlock amount (move from locked to free)."""
        if amount <= 0:
            raise ValueError(f"Amount must be positive: {amount}")
        if self.locked < amount:
            raise ValueError(f"Insufficient locked balance: {self.locked} < {amount}")
        self.locked -= amount
        self.free += amount
        self.updated_at = datetime.now(timezone.utc)
    
    def __repr__(self) -> str:
        return f"Balance(asset={self.asset}, free={self.free}, locked={self.locked}, total={self.total})"
