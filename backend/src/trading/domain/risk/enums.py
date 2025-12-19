from enum import Enum


class RiskLevel(str, Enum):
    """Risk levels for position sizing and management."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"  
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RiskLimitType(str, Enum):
    """Types of risk limits that can be applied."""
    POSITION_SIZE = "POSITION_SIZE"
    DAILY_LOSS = "DAILY_LOSS"
    DRAWDOWN = "DRAWDOWN"
    LEVERAGE = "LEVERAGE"
    EXPOSURE = "EXPOSURE"


class RiskStatus(str, Enum):
    """Status of risk monitoring."""
    NORMAL = "NORMAL"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    BREACHED = "BREACHED"


class AlertType(str, Enum):
    """Types of risk alerts."""
    POSITION_LIMIT_APPROACHED = "POSITION_LIMIT_APPROACHED"
    POSITION_LIMIT_EXCEEDED = "POSITION_LIMIT_EXCEEDED"
    DAILY_LOSS_LIMIT_APPROACHED = "DAILY_LOSS_LIMIT_APPROACHED"
    DAILY_LOSS_LIMIT_EXCEEDED = "DAILY_LOSS_LIMIT_EXCEEDED"
    DRAWDOWN_LIMIT_APPROACHED = "DRAWDOWN_LIMIT_APPROACHED"
    DRAWDOWN_LIMIT_EXCEEDED = "DRAWDOWN_LIMIT_EXCEEDED"
    MARGIN_CALL = "MARGIN_CALL"
    LIQUIDATION_WARNING = "LIQUIDATION_WARNING"