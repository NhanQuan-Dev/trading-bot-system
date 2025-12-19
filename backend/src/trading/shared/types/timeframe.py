"""
Timeframe value object
"""

from dataclasses import dataclass
from enum import Enum
from src.trading.shared.kernel.value_object import ValueObject


class TimeframeUnit(str, Enum):
    """Timeframe unit enum"""
    SECOND = "s"
    MINUTE = "m"
    HOUR = "h"
    DAY = "d"
    WEEK = "w"
    MONTH = "M"


@dataclass(frozen=True)
class Timeframe(ValueObject):
    """
    Timeframe value object representing a time period
    """
    
    value: int
    unit: TimeframeUnit
    
    def __post_init__(self):
        if self.value <= 0:
            raise ValueError("Timeframe value must be positive")
    
    @property
    def code(self) -> str:
        """Get timeframe code (e.g., '1m', '4h', '1d')"""
        return f"{self.value}{self.unit.value}"
    
    @property
    def seconds(self) -> int:
        """Convert timeframe to seconds"""
        multipliers = {
            TimeframeUnit.SECOND: 1,
            TimeframeUnit.MINUTE: 60,
            TimeframeUnit.HOUR: 3600,
            TimeframeUnit.DAY: 86400,
            TimeframeUnit.WEEK: 604800,
            TimeframeUnit.MONTH: 2592000,  # Approximate
        }
        return self.value * multipliers[self.unit]
    
    def __str__(self) -> str:
        return self.code
    
    @classmethod
    def from_string(cls, timeframe_str: str) -> "Timeframe":
        """
        Create Timeframe from string like '1m', '4h', '1d'
        """
        unit_str = timeframe_str[-1]
        value_str = timeframe_str[:-1]
        
        try:
            value = int(value_str)
            unit = TimeframeUnit(unit_str)
            return cls(value=value, unit=unit)
        except (ValueError, KeyError):
            raise ValueError(f"Invalid timeframe format: {timeframe_str}")
    
    # Common timeframes
    @classmethod
    def ONE_MINUTE(cls) -> "Timeframe":
        return cls(1, TimeframeUnit.MINUTE)
    
    @classmethod
    def FIVE_MINUTES(cls) -> "Timeframe":
        return cls(5, TimeframeUnit.MINUTE)
    
    @classmethod
    def FIFTEEN_MINUTES(cls) -> "Timeframe":
        return cls(15, TimeframeUnit.MINUTE)
    
    @classmethod
    def ONE_HOUR(cls) -> "Timeframe":
        return cls(1, TimeframeUnit.HOUR)
    
    @classmethod
    def FOUR_HOURS(cls) -> "Timeframe":
        return cls(4, TimeframeUnit.HOUR)
    
    @classmethod
    def ONE_DAY(cls) -> "Timeframe":
        return cls(1, TimeframeUnit.DAY)
