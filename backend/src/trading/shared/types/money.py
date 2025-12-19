"""
Money value object
"""

from dataclasses import dataclass
from decimal import Decimal
from src.trading.shared.kernel.value_object import ValueObject


@dataclass(frozen=True)
class Money(ValueObject):
    """
    Money value object representing an amount in a specific currency
    """
    
    amount: Decimal
    currency: str = "USDT"
    
    def __post_init__(self):
        if self.amount < 0:
            raise ValueError("Money amount cannot be negative")
        if not self.currency:
            raise ValueError("Currency must be specified")
    
    def add(self, other: "Money") -> "Money":
        """Add two money amounts"""
        if self.currency != other.currency:
            raise ValueError(f"Cannot add different currencies: {self.currency} and {other.currency}")
        return Money(self.amount + other.amount, self.currency)
    
    def subtract(self, other: "Money") -> "Money":
        """Subtract money amounts"""
        if self.currency != other.currency:
            raise ValueError(f"Cannot subtract different currencies: {self.currency} and {other.currency}")
        return Money(self.amount - other.amount, self.currency)
    
    def multiply(self, factor: Decimal | float) -> "Money":
        """Multiply money by a factor"""
        return Money(self.amount * Decimal(str(factor)), self.currency)
    
    def is_zero(self) -> bool:
        """Check if amount is zero"""
        return self.amount == Decimal("0")
    
    def is_positive(self) -> bool:
        """Check if amount is positive"""
        return self.amount > Decimal("0")
    
    def is_negative(self) -> bool:
        """Check if amount is negative"""
        return self.amount < Decimal("0")
    
    def __str__(self) -> str:
        return f"{self.amount:.8f} {self.currency}"
    
    @classmethod
    def zero(cls, currency: str = "USDT") -> "Money":
        """Create zero money"""
        return cls(Decimal("0"), currency)
