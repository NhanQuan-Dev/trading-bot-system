"""Portfolio aggregate root - manages account state"""
from decimal import Decimal
from typing import Dict, Optional
from datetime import datetime
import uuid

from src.trading.shared.kernel.aggregate_root import AggregateRoot
from src.trading.shared.types.symbol import Symbol
from src.trading.shared.types.money import Money
from src.trading.shared.errors.domain_errors import InsufficientBalanceError

from ..value_objects.asset_balance import AssetBalance
from ..entities.asset_position import AssetPosition, PositionSide
from ..events import (
    BalanceUpdatedEvent,
    PositionOpenedEvent,
    PositionClosedEvent,
    EquityChangedEvent,
)


class PortfolioAggregate(AggregateRoot):
    """
    Aggregate root managing portfolio state (balances + positions).
    
    Responsibilities:
        - Manage account balances (free + locked)
        - Manage open positions
        - Calculate total equity
        - Enforce margin requirements
        - Emit domain events on state changes
    
    Invariants:
        - Total balance = free + locked
        - Position margin <= available balance
        - Cannot open position without sufficient balance
        - All balances must be non-negative
    """
    
    def __init__(self, account_id: str):
        super().__init__()
        
        if not account_id or not account_id.strip():
            raise ValueError("account_id cannot be empty")
        
        self._account_id = account_id.strip()
        self._balances: Dict[str, AssetBalance] = {}
        self._positions: Dict[str, AssetPosition] = {}
        self._total_equity = Money(Decimal(0), "USDT")
    
    @property
    def account_id(self) -> str:
        """Account identifier (immutable)"""
        return self._account_id
    
    @property
    def balances(self) -> Dict[str, AssetBalance]:
        """Copy of balances (read-only)"""
        return self._balances.copy()
    
    @property
    def positions(self) -> Dict[str, AssetPosition]:
        """Copy of positions (read-only)"""
        return self._positions.copy()
    
    def update_balance(self, asset: str, free: Decimal, locked: Decimal) -> None:
        """
        Update asset balance.
        
        Args:
            asset: Asset symbol
            free: Free balance
            locked: Locked balance
        
        Emits:
            BalanceUpdatedEvent
        """
        asset = asset.upper().strip()
        
        # Get old balance for event
        old_balance = self._balances.get(asset)
        old_free = old_balance.free if old_balance else Decimal(0)
        old_locked = old_balance.locked if old_balance else Decimal(0)
        
        # Update balance
        new_balance = AssetBalance(asset, free, locked)
        self._balances[asset] = new_balance
        
        # Emit event
        self.add_domain_event(
            BalanceUpdatedEvent(
                account_id=self._account_id,
                asset=asset,
                free=free,
                locked=locked,
                old_free=old_free,
                old_locked=old_locked
            )
        )
        
        # Check if equity changed significantly
        self._check_equity_change("balance_update")
    
    def open_position(
        self,
        symbol: Symbol,
        quantity: Decimal,
        side: str,
        entry_price: Decimal,
        leverage: int
    ) -> str:
        """
        Open new position.
        
        Args:
            symbol: Trading pair symbol
            quantity: Position size
            side: LONG or SHORT
            entry_price: Entry price
            leverage: Position leverage
        
        Returns:
            Position ID
        
        Raises:
            InsufficientBalanceError: If not enough balance for margin
            ValueError: If position already exists for symbol
        
        Emits:
            PositionOpenedEvent
        """
        symbol_str = symbol.to_exchange_format()
        
        # Check if position already exists
        if symbol_str in self._positions:
            raise ValueError(f"Position already exists for {symbol_str}")
        
        # Calculate required margin
        notional_value = quantity * entry_price
        required_margin = notional_value / leverage
        
        # Check sufficient balance
        available_balance = self._get_available_balance("USDT")
        if required_margin > available_balance:
            raise InsufficientBalanceError(
                f"Need {required_margin} USDT margin, "
                f"have {available_balance} USDT available"
            )
        
        # Create position
        position_id = str(uuid.uuid4())
        position = AssetPosition(
            position_id=position_id,
            symbol=symbol,
            quantity=quantity,
            side=side,
            entry_price=entry_price,
            leverage=leverage,
            opened_at=datetime.utcnow()
        )
        
        # Lock margin
        usdt_balance = self._balances.get("USDT")
        if usdt_balance:
            self._balances["USDT"] = usdt_balance.lock(required_margin)
        
        # Add position
        self._positions[symbol_str] = position
        
        # Emit event
        self.add_domain_event(
            PositionOpenedEvent(
                account_id=self._account_id,
                position_id=position_id,
                symbol=symbol_str,
                side=side,
                quantity=quantity,
                entry_price=entry_price,
                leverage=leverage,
                margin_used=required_margin
            )
        )
        
        return position_id
    
    def close_position(self, symbol: str, exit_price: Decimal) -> Decimal:
        """
        Close existing position.
        
        Args:
            symbol: Trading pair symbol
            exit_price: Exit price
        
        Returns:
            Realized P&L
        
        Raises:
            ValueError: If position doesn't exist
        
        Emits:
            PositionClosedEvent
        """
        symbol = symbol.upper()
        
        if symbol not in self._positions:
            raise ValueError(f"No position found for {symbol}")
        
        position = self._positions[symbol]
        
        # Calculate realized P&L
        realized_pnl = position.calculate_pnl(exit_price)
        
        # Release margin
        margin_to_release = position.margin_used
        usdt_balance = self._balances.get("USDT")
        if usdt_balance:
            self._balances["USDT"] = usdt_balance.unlock(margin_to_release)
            # Add P&L to balance
            self._balances["USDT"] = self._balances["USDT"].add(realized_pnl)
        
        # Emit event
        self.add_domain_event(
            PositionClosedEvent(
                account_id=self._account_id,
                position_id=position.id,
                symbol=symbol,
                side=position.side,
                quantity=position.quantity,
                entry_price=position.entry_price,
                exit_price=exit_price,
                realized_pnl=realized_pnl,
                margin_released=margin_to_release
            )
        )
        
        # Remove position
        del self._positions[symbol]
        
        # Check equity change
        self._check_equity_change("position_closed")
        
        return realized_pnl
    
    def update_position_pnl(self, symbol: str, current_price: Decimal) -> None:
        """
        Update position's unrealized P&L.
        
        Args:
            symbol: Trading pair symbol
            current_price: Current market price
        """
        symbol = symbol.upper()
        
        if symbol in self._positions:
            position = self._positions[symbol]
            position.calculate_pnl(current_price)
    
    def calculate_total_equity(self, market_prices: Optional[Dict[str, Decimal]] = None) -> Money:
        """
        Calculate total equity (balance + unrealized P&L).
        
        Args:
            market_prices: Current market prices for positions (optional)
        
        Returns:
            Total equity in USDT
        """
        # Sum all balances (convert to USDT if needed)
        total_balance = Decimal(0)
        for asset, balance in self._balances.items():
            if asset == "USDT":
                total_balance += balance.total
            # TODO: Add conversion for other assets
        
        # Add unrealized P&L from positions
        total_unrealized_pnl = Decimal(0)
        if market_prices:
            for symbol, position in self._positions.items():
                if symbol in market_prices:
                    pnl = position.calculate_pnl(market_prices[symbol])
                    total_unrealized_pnl += pnl
        else:
            # Use cached unrealized P&L
            for position in self._positions.values():
                total_unrealized_pnl += position.unrealized_pnl
        
        total_equity = total_balance + total_unrealized_pnl
        self._total_equity = Money(total_equity, "USDT")
        
        return self._total_equity
    
    def get_available_balance(self, asset: str = "USDT") -> Decimal:
        """
        Get available balance for asset.
        
        Args:
            asset: Asset symbol (default: USDT)
        
        Returns:
            Available balance (free)
        """
        return self._get_available_balance(asset)
    
    def get_position(self, symbol: str) -> Optional[AssetPosition]:
        """
        Get position by symbol.
        
        Args:
            symbol: Trading pair symbol
        
        Returns:
            Position or None
        """
        return self._positions.get(symbol.upper())
    
    def has_position(self, symbol: str) -> bool:
        """Check if position exists for symbol"""
        return symbol.upper() in self._positions
    
    def get_total_margin_used(self) -> Decimal:
        """Calculate total margin used across all positions"""
        return sum(pos.margin_used for pos in self._positions.values())
    
    def get_total_unrealized_pnl(self) -> Decimal:
        """Get total unrealized P&L across all positions"""
        return sum(pos.unrealized_pnl for pos in self._positions.values())
    
    # Private helper methods
    
    def _get_available_balance(self, asset: str) -> Decimal:
        """Get available balance (private)"""
        asset = asset.upper()
        balance = self._balances.get(asset)
        return balance.free if balance else Decimal(0)
    
    def _check_equity_change(self, reason: str) -> None:
        """Check if equity changed significantly and emit event"""
        old_equity = self._total_equity.amount
        new_equity = self.calculate_total_equity().amount
        
        if old_equity == 0:
            return
        
        change_percentage = ((new_equity - old_equity) / old_equity) * 100
        
        # Emit event if change > 1%
        if abs(change_percentage) > Decimal("1.0"):
            self.add_domain_event(
                EquityChangedEvent(
                    account_id=self._account_id,
                    old_equity=old_equity,
                    new_equity=new_equity,
                    change_percentage=change_percentage,
                    reason=reason
                )
            )
    
    def __repr__(self) -> str:
        return (
            f"PortfolioAggregate(account_id={self._account_id}, "
            f"balances={len(self._balances)}, "
            f"positions={len(self._positions)}, "
            f"equity={self._total_equity})"
        )
