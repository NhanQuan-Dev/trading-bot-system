"""Backtesting domain module."""

from .entities import (
    BacktestRun,
    BacktestTrade,
    BacktestPosition,
    BacktestResults,
)
from .value_objects import (
    PerformanceMetrics,
    DrawdownInfo,
    TradeStatistics,
    TimeframeReturns,
    BacktestConfig,
    EquityCurvePoint,
)
from .enums import (
    BacktestStatus,
    BacktestMode,
    SlippageModel,
    CommissionModel,
    PositionSizing,
    TradeDirection,
)
from .repositories import IBacktestRepository

__all__ = [
    # Entities
    "BacktestRun",
    "BacktestTrade",
    "BacktestPosition",
    "BacktestResults",
    # Value Objects
    "PerformanceMetrics",
    "DrawdownInfo",
    "TradeStatistics",
    "TimeframeReturns",
    "BacktestConfig",
    "EquityCurvePoint",
    # Enums
    "BacktestStatus",
    "BacktestMode",
    "SlippageModel",
    "CommissionModel",
    "PositionSizing",
    "TradeDirection",
    # Repositories
    "IBacktestRepository",
]
