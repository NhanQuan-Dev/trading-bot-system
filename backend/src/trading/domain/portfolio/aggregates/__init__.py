"""Portfolio Aggregate Root - manages balances and positions."""
from decimal import Decimal
from typing import Dict, List, Optional
from datetime import datetime, timezone
import uuid

from ..entities import Position, Balance
from ..value_objects import PositionSide, MarginMode, Leverage, PnL
from ..events import (
    BalanceUpdatedEvent,
    PositionOpenedEvent,
    PositionClosedEvent,
    PositionUpdatedEvent,
    MarginCallEvent,
    LiquidationEvent,
    EquityChangedEvent,
)


class Portfolio:
    """
    Portfolio Aggregate Root.
    
    Manages user's balances and positions across all symbols and exchanges.
    Enforces business rules and emits domain events.
    """
    
    def __init__(self, user_id: uuid.UUID):
        self.user_id = user_id
        self.balances: Dict[str, Balance] = {}  # asset -> Balance
        self.positions: Dict[uuid.UUID, Position] = {}  # position_id -> Position
        self._domain_events: List[object] = []
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
    
    # ==================== Balance Management ====================
    
    def add_balance(self, asset: str, free: Decimal, locked: Decimal = Decimal("0")) -> None:
        """Add or update asset balance."""
        if asset in self.balances:
            old_free = self.balances[asset].free
            old_locked = self.balances[asset].locked
            self.balances[asset].free = free
            self.balances[asset].locked = locked
            self.balances[asset].updated_at = datetime.now(timezone.utc)
            
            # Emit balance updated event
            self._add_event(BalanceUpdatedEvent(
                event_id=uuid.uuid4(),
                occurred_at=datetime.now(timezone.utc),
                user_id=self.user_id,
                asset=asset,
                old_free=old_free,
                new_free=free,
                old_locked=old_locked,
                new_locked=locked,
                reason="balance_sync"
            ))
        else:
            self.balances[asset] = Balance(
                user_id=self.user_id,
                asset=asset,
                free=free,
                locked=locked
            )
        
        self.updated_at = datetime.now(timezone.utc)
    
    def get_balance(self, asset: str) -> Optional[Balance]:
        """Get balance for asset."""
        return self.balances.get(asset)
    
    def get_available_balance(self, asset: str) -> Decimal:
        """Get available (free) balance for asset."""
        balance = self.balances.get(asset)
        return balance.free if balance else Decimal("0")
    
    def deposit(self, asset: str, amount: Decimal) -> None:
        """Deposit funds to portfolio."""
        if amount <= 0:
            raise ValueError(f"Deposit amount must be positive: {amount}")
        
        old_free = self.get_available_balance(asset)
        
        if asset in self.balances:
            self.balances[asset].add_free(amount)
        else:
            self.balances[asset] = Balance(
                user_id=self.user_id,
                asset=asset,
                free=amount,
                locked=Decimal("0")
            )
        
        self._add_event(BalanceUpdatedEvent(
            event_id=uuid.uuid4(),
            occurred_at=datetime.now(timezone.utc),
            user_id=self.user_id,
            asset=asset,
            old_free=old_free,
            new_free=self.balances[asset].free,
            old_locked=self.balances[asset].locked,
            new_locked=self.balances[asset].locked,
            reason="deposit"
        ))
        
        self.updated_at = datetime.now(timezone.utc)
    
    def withdraw(self, asset: str, amount: Decimal) -> None:
        """Withdraw funds from portfolio."""
        if amount <= 0:
            raise ValueError(f"Withdraw amount must be positive: {amount}")
        
        balance = self.balances.get(asset)
        if not balance:
            raise ValueError(f"No balance for asset: {asset}")
        
        if balance.free < amount:
            raise ValueError(
                f"Insufficient balance for withdrawal: available={balance.free}, requested={amount}"
            )
        
        old_free = balance.free
        balance.subtract_free(amount)
        
        self._add_event(BalanceUpdatedEvent(
            event_id=uuid.uuid4(),
            occurred_at=datetime.now(timezone.utc),
            user_id=self.user_id,
            asset=asset,
            old_free=old_free,
            new_free=balance.free,
            old_locked=balance.locked,
            new_locked=balance.locked,
            reason="withdraw"
        ))
        
        self.updated_at = datetime.now(timezone.utc)
    
    # ==================== Position Management ====================
    
    def open_position(
        self,
        symbol: str,
        side: PositionSide,
        entry_price: Decimal,
        quantity: Decimal,
        leverage: Leverage,
        margin_mode: MarginMode,
        quote_asset: str = "USDT",
        bot_id: Optional[uuid.UUID] = None,
        stop_loss: Optional[Decimal] = None,
        take_profit: Optional[Decimal] = None,
    ) -> Position:
        """Open a new position."""
        # Validate inputs
        if entry_price <= 0:
            raise ValueError(f"Entry price must be positive: {entry_price}")
        if quantity <= 0:
            raise ValueError(f"Quantity must be positive: {quantity}")
        
        # Create position
        position_id = uuid.uuid4()
        position = Position(
            id=position_id,
            user_id=self.user_id,
            symbol=symbol,
            side=side,
            entry_price=entry_price,
            quantity=quantity,
            leverage=leverage,
            margin_mode=margin_mode,
            bot_id=bot_id,
            stop_loss=stop_loss,
            take_profit=take_profit,
        )
        
        # Check if we have enough margin
        required_margin = position.margin_used
        available = self.get_available_balance(quote_asset)
        
        if available < required_margin:
            raise ValueError(
                f"Insufficient margin: required={required_margin}, available={available}"
            )
        
        # Lock margin
        self.balances[quote_asset].lock(required_margin)
        
        # Add position
        self.positions[position_id] = position
        
        # Emit events
        self._add_event(PositionOpenedEvent(
            event_id=uuid.uuid4(),
            occurred_at=datetime.now(timezone.utc),
            position_id=position_id,
            user_id=self.user_id,
            bot_id=bot_id,
            symbol=symbol,
            side=side,
            entry_price=entry_price,
            quantity=quantity,
            leverage=leverage.value,
            margin_used=required_margin,
        ))
        
        self.updated_at = datetime.now(timezone.utc)
        return position
    
    def close_position(
        self,
        position_id: uuid.UUID,
        close_price: Decimal,
        quote_asset: str = "USDT",
        close_reason: str = "manual"
    ) -> Decimal:
        """Close an existing position."""
        position = self.positions.get(position_id)
        if not position:
            raise ValueError(f"Position not found: {position_id}")
        
        # Calculate realized P&L
        realized_pnl = position.close(close_price)
        
        # Unlock margin and add/subtract P&L
        margin_used = position.margin_used
        final_amount = margin_used + realized_pnl
        
        self.balances[quote_asset].unlock(margin_used)
        
        if realized_pnl > 0:
            self.balances[quote_asset].add_free(realized_pnl)
        elif realized_pnl < 0:
            self.balances[quote_asset].subtract_free(abs(realized_pnl))
        
        # Calculate ROE
        roe = position.pnl.calculate_roe(margin_used)
        
        # Remove position
        del self.positions[position_id]
        
        # Emit event
        self._add_event(PositionClosedEvent(
            event_id=uuid.uuid4(),
            occurred_at=datetime.now(timezone.utc),
            position_id=position_id,
            user_id=self.user_id,
            bot_id=position.bot_id,
            symbol=position.symbol,
            side=position.side,
            entry_price=position.entry_price,
            close_price=close_price,
            quantity=position.quantity,
            realized_pnl=realized_pnl,
            roe=roe,
            close_reason=close_reason,
        ))
        
        self.updated_at = datetime.now(timezone.utc)
        return realized_pnl
    
    def update_position_price(self, position_id: uuid.UUID, new_price: Decimal) -> None:
        """Update position mark price and recalculate P&L."""
        position = self.positions.get(position_id)
        if not position:
            raise ValueError(f"Position not found: {position_id}")
        
        old_price = position.mark_price
        old_pnl = position.pnl.unrealized
        
        position.update_mark_price(new_price)
        
        # Emit event
        self._add_event(PositionUpdatedEvent(
            event_id=uuid.uuid4(),
            occurred_at=datetime.now(timezone.utc),
            position_id=position_id,
            user_id=self.user_id,
            symbol=position.symbol,
            old_mark_price=old_price,
            new_mark_price=new_price,
            old_unrealized_pnl=old_pnl,
            new_unrealized_pnl=position.pnl.unrealized,
        ))
        
        # Check for liquidation
        if position.should_liquidate():
            self._handle_liquidation(position)
        
        self.updated_at = datetime.now(timezone.utc)
    
    def _handle_liquidation(self, position: Position) -> None:
        """Handle position liquidation."""
        # Emit liquidation event
        self._add_event(LiquidationEvent(
            event_id=uuid.uuid4(),
            occurred_at=datetime.now(timezone.utc),
            position_id=position.id,
            user_id=self.user_id,
            bot_id=position.bot_id,
            symbol=position.symbol,
            side=position.side,
            liquidation_price=position.liquidation_price or Decimal("0"),
            quantity=position.quantity,
            loss_amount=abs(position.pnl.unrealized),
        ))
        
        # Close position at liquidation price
        if position.liquidation_price:
            self.close_position(
                position_id=position.id,
                close_price=position.liquidation_price,
                close_reason="liquidation"
            )
    
    def get_position(self, position_id: uuid.UUID) -> Optional[Position]:
        """Get position by ID."""
        return self.positions.get(position_id)
    
    def get_positions_by_symbol(self, symbol: str) -> List[Position]:
        """Get all positions for a symbol."""
        return [p for p in self.positions.values() if p.symbol == symbol]
    
    def get_open_positions(self) -> List[Position]:
        """Get all open positions."""
        return list(self.positions.values())
    
    # ==================== Portfolio Metrics ====================
    
    def calculate_total_equity(self) -> Decimal:
        """Calculate total portfolio equity (balances + unrealized P&L)."""
        balances_total = sum(b.total for b in self.balances.values())
        unrealized_pnl = sum(p.pnl.unrealized for p in self.positions.values())
        return balances_total + unrealized_pnl
    
    def calculate_margin_used(self) -> Decimal:
        """Calculate total margin used across all positions."""
        return sum(p.margin_used for p in self.positions.values())
    
    def calculate_margin_ratio(self) -> Decimal:
        """Calculate portfolio margin ratio."""
        equity = self.calculate_total_equity()
        margin_used = self.calculate_margin_used()
        
        if margin_used == 0:
            return Decimal("0")
        
        return equity / margin_used
    
    def calculate_total_unrealized_pnl(self) -> Decimal:
        """Calculate total unrealized P&L across all positions."""
        return sum(p.pnl.unrealized for p in self.positions.values())
    
    # ==================== Domain Events ====================
    
    def _add_event(self, event: object) -> None:
        """Add domain event to the event list."""
        self._domain_events.append(event)
    
    def collect_events(self) -> List[object]:
        """Collect and clear all domain events."""
        events = self._domain_events.copy()
        self._domain_events.clear()
        return events
    
    def __repr__(self) -> str:
        return (
            f"Portfolio(user_id={self.user_id}, "
            f"balances={len(self.balances)}, "
            f"positions={len(self.positions)}, "
            f"equity={self.calculate_total_equity()})"
        )
