"""AssetBalance value object - represents balance for an asset"""
from decimal import Decimal
from src.trading.shared.kernel.value_object import ValueObject


class AssetBalance(ValueObject):
    """
    Immutable value object representing an asset balance.
    
    Attributes:
        asset: Asset symbol (e.g., 'USDT', 'BTC')
        free: Available balance
        locked: Locked balance (in orders, positions)
    
    Business Rules:
        - Balance cannot be negative
        - Asset symbol is case-insensitive (stored as uppercase)
        - Total = free + locked
    """
    
    def __init__(self, asset: str, free: Decimal, locked: Decimal):
        if not asset or not asset.strip():
            raise ValueError("Asset symbol cannot be empty")
        
        if free < 0:
            raise ValueError(f"Free balance cannot be negative: {free}")
        
        if locked < 0:
            raise ValueError(f"Locked balance cannot be negative: {locked}")
        
        self._asset = asset.upper().strip()
        self._free = free
        self._locked = locked
    
    @property
    def asset(self) -> str:
        """Asset symbol"""
        return self._asset
    
    @property
    def free(self) -> Decimal:
        """Available balance"""
        return self._free
    
    @property
    def locked(self) -> Decimal:
        """Locked balance"""
        return self._locked
    
    @property
    def total(self) -> Decimal:
        """Total balance (free + locked)"""
        return self._free + self._locked
    
    def lock(self, amount: Decimal) -> 'AssetBalance':
        """
        Lock specified amount from free balance.
        
        Args:
            amount: Amount to lock
        
        Returns:
            New AssetBalance instance with updated balances
        
        Raises:
            ValueError: If amount > free balance
        """
        if amount < 0:
            raise ValueError(f"Cannot lock negative amount: {amount}")
        
        if amount > self._free:
            raise ValueError(
                f"Cannot lock {amount} {self._asset}, only {self._free} available"
            )
        
        return AssetBalance(
            self._asset,
            self._free - amount,
            self._locked + amount
        )
    
    def unlock(self, amount: Decimal) -> 'AssetBalance':
        """
        Unlock specified amount to free balance.
        
        Args:
            amount: Amount to unlock
        
        Returns:
            New AssetBalance instance with updated balances
        
        Raises:
            ValueError: If amount > locked balance
        """
        if amount < 0:
            raise ValueError(f"Cannot unlock negative amount: {amount}")
        
        if amount > self._locked:
            raise ValueError(
                f"Cannot unlock {amount} {self._asset}, only {self._locked} locked"
            )
        
        return AssetBalance(
            self._asset,
            self._free + amount,
            self._locked - amount
        )
    
    def add(self, amount: Decimal) -> 'AssetBalance':
        """
        Add amount to free balance.
        
        Args:
            amount: Amount to add (can be negative for subtraction)
        
        Returns:
            New AssetBalance instance
        """
        new_free = self._free + amount
        
        if new_free < 0:
            raise ValueError(
                f"Resulting free balance cannot be negative: {new_free}"
            )
        
        return AssetBalance(self._asset, new_free, self._locked)
    
    def __eq__(self, other) -> bool:
        """Value equality"""
        if not isinstance(other, AssetBalance):
            return False
        
        return (
            self._asset == other._asset and
            self._free == other._free and
            self._locked == other._locked
        )
    
    def __hash__(self) -> int:
        return hash((self._asset, self._free, self._locked))
    
    def __repr__(self) -> str:
        return (
            f"AssetBalance(asset={self._asset}, "
            f"free={self._free}, locked={self._locked})"
        )
