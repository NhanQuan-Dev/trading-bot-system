"""AssetPosition entity - represents an open position"""
from decimal import Decimal
from datetime import datetime
from typing import Optional
from src.trading.shared.kernel.entity import Entity
from src.trading.shared.types.symbol import Symbol


class PositionSide:
    """Position side enum"""
    LONG = "LONG"
    SHORT = "SHORT"


class AssetPosition(Entity):
    """
    Entity representing an open trading position.
    
    Attributes:
        symbol: Trading pair symbol
        quantity: Position size (always positive)
        side: LONG or SHORT
        entry_price: Average entry price
        leverage: Position leverage
        opened_at: Timestamp when position was opened
        unrealized_pnl: Current unrealized profit/loss
    
    Business Rules:
        - Quantity must be positive
        - Leverage must be between 1 and 125
        - Entry price must be positive
    """
    
    def __init__(
        self,
        position_id: str,
        symbol: Symbol,
        quantity: Decimal,
        side: str,
        entry_price: Decimal,
        leverage: int,
        opened_at: Optional[datetime] = None
    ):
        super().__init__(position_id)
        
        # Validation
        if quantity <= 0:
            raise ValueError(f"Quantity must be positive: {quantity}")
        
        if entry_price <= 0:
            raise ValueError(f"Entry price must be positive: {entry_price}")
        
        if leverage < 1 or leverage > 125:
            raise ValueError(f"Leverage must be between 1 and 125: {leverage}")
        
        if side not in [PositionSide.LONG, PositionSide.SHORT]:
            raise ValueError(f"Invalid position side: {side}")
        
        self._symbol = symbol
        self._quantity = quantity
        self._side = side
        self._entry_price = entry_price
        self._leverage = leverage
        self._opened_at = opened_at or datetime.utcnow()
        self._unrealized_pnl = Decimal(0)
    
    @property
    def symbol(self) -> Symbol:
        """Trading pair symbol"""
        return self._symbol
    
    @property
    def quantity(self) -> Decimal:
        """Position size"""
        return self._quantity
    
    @property
    def side(self) -> str:
        """Position side (LONG/SHORT)"""
        return self._side
    
    @property
    def entry_price(self) -> Decimal:
        """Average entry price"""
        return self._entry_price
    
    @property
    def leverage(self) -> int:
        """Position leverage"""
        return self._leverage
    
    @property
    def opened_at(self) -> datetime:
        """When position was opened"""
        return self._opened_at
    
    @property
    def unrealized_pnl(self) -> Decimal:
        """Current unrealized P&L"""
        return self._unrealized_pnl
    
    @property
    def notional_value(self) -> Decimal:
        """Position notional value (quantity * price)"""
        return self._quantity * self._entry_price
    
    @property
    def margin_used(self) -> Decimal:
        """Margin used for this position"""
        return self.notional_value / self._leverage
    
    def calculate_pnl(self, current_price: Decimal) -> Decimal:
        """
        Calculate unrealized P&L at current price.
        
        Args:
            current_price: Current market price
        
        Returns:
            Unrealized P&L (positive = profit, negative = loss)
        """
        if current_price <= 0:
            raise ValueError(f"Current price must be positive: {current_price}")
        
        price_diff = current_price - self._entry_price
        
        if self._side == PositionSide.SHORT:
            price_diff = -price_diff
        
        pnl = price_diff * self._quantity
        self._unrealized_pnl = pnl
        
        return pnl
    
    def calculate_pnl_percentage(self, current_price: Decimal) -> Decimal:
        """
        Calculate P&L as percentage of entry value.
        
        Args:
            current_price: Current market price
        
        Returns:
            P&L percentage (with leverage)
        """
        pnl = self.calculate_pnl(current_price)
        margin = self.margin_used
        
        if margin == 0:
            return Decimal(0)
        
        return (pnl / margin) * 100
    
    def calculate_liquidation_price(self, maintenance_margin_rate: Decimal = Decimal("0.004")) -> Decimal:
        """
        Calculate liquidation price.
        
        Args:
            maintenance_margin_rate: Maintenance margin rate (default 0.4%)
        
        Returns:
            Liquidation price
        """
        if self._side == PositionSide.LONG:
            # Long liquidation: entry_price * (1 - 1/leverage + maintenance_margin_rate)
            liquidation = self._entry_price * (
                Decimal(1) - Decimal(1) / self._leverage + maintenance_margin_rate
            )
        else:
            # Short liquidation: entry_price * (1 + 1/leverage - maintenance_margin_rate)
            liquidation = self._entry_price * (
                Decimal(1) + Decimal(1) / self._leverage - maintenance_margin_rate
            )
        
        return liquidation
    
    def increase_position(self, quantity: Decimal, price: Decimal) -> None:
        """
        Increase position size (calculate new average entry price).
        
        Args:
            quantity: Additional quantity
            price: Fill price
        """
        if quantity <= 0:
            raise ValueError(f"Quantity must be positive: {quantity}")
        
        if price <= 0:
            raise ValueError(f"Price must be positive: {price}")
        
        # Calculate new average entry price
        old_notional = self._quantity * self._entry_price
        new_notional = quantity * price
        total_quantity = self._quantity + quantity
        
        self._entry_price = (old_notional + new_notional) / total_quantity
        self._quantity = total_quantity
    
    def reduce_position(self, quantity: Decimal) -> Decimal:
        """
        Reduce position size (partial close).
        
        Args:
            quantity: Quantity to reduce
        
        Returns:
            Realized P&L from the reduction
        
        Raises:
            ValueError: If quantity > position size
        """
        if quantity <= 0:
            raise ValueError(f"Quantity must be positive: {quantity}")
        
        if quantity > self._quantity:
            raise ValueError(
                f"Cannot reduce by {quantity}, position size is {self._quantity}"
            )
        
        # Calculate realized P&L for the reduced portion
        proportion = quantity / self._quantity
        realized_pnl = self._unrealized_pnl * proportion
        
        # Update position
        self._quantity -= quantity
        self._unrealized_pnl -= realized_pnl
        
        return realized_pnl
    
    def __repr__(self) -> str:
        return (
            f"AssetPosition(id={self.id}, symbol={self._symbol}, "
            f"side={self._side}, quantity={self._quantity}, "
            f"entry={self._entry_price}, leverage={self._leverage}x)"
        )
