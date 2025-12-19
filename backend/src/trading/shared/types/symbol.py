"""
Symbol value object
"""

from dataclasses import dataclass
from src.trading.shared.kernel.value_object import ValueObject


@dataclass(frozen=True)
class Symbol(ValueObject):
    """
    Trading symbol value object
    """
    
    base: str
    quote: str
    exchange: str = "BINANCE"
    
    def __post_init__(self):
        if not self.base or not self.quote:
            raise ValueError("Base and quote currency must be specified")
    
    @property
    def pair(self) -> str:
        """Get trading pair (e.g., BTCUSDT)"""
        return f"{self.base}{self.quote}"
    
    @property
    def display(self) -> str:
        """Get display format (e.g., BTC/USDT)"""
        return f"{self.base}/{self.quote}"
    
    def to_exchange_format(self) -> str:
        """Get exchange format (same as pair)"""
        return self.pair
    
    def __str__(self) -> str:
        return self.pair
    
    @classmethod
    def from_string(cls, symbol_str: str, exchange: str = "BINANCE") -> "Symbol":
        """
        Create Symbol from string like 'BTCUSDT'
        Assumes common quote currencies: USDT, BUSD, USD, BTC, ETH
        """
        quote_currencies = ["USDT", "BUSD", "USD", "BTC", "ETH", "BNB"]
        
        for quote in quote_currencies:
            if symbol_str.endswith(quote):
                base = symbol_str[:-len(quote)]
                return cls(base=base, quote=quote, exchange=exchange)
        
        raise ValueError(f"Cannot parse symbol: {symbol_str}")
