"""Backtesting request/response schemas."""

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict

from ...domain.backtesting import (
    BacktestStatus,
    BacktestMode,
    SlippageModel,
    CommissionModel,
    PositionSizing,
    TradeDirection,
)


# Request schemas
class BacktestConfigRequest(BaseModel):
    """Backtest configuration request."""
    
    symbol: str = Field(..., description="Trading symbol")
    timeframe: str = Field(..., description="Candlestick timeframe")
    start_date: datetime = Field(..., description="Backtest start date")
    end_date: datetime = Field(..., description="Backtest end date")
    initial_capital: Decimal = Field(..., description="Initial capital", gt=0)
    
    # Position sizing
    position_sizing: PositionSizing = Field(
        default=PositionSizing.PERCENT_EQUITY,
        description="Position sizing method"
    )
    position_size_percent: Optional[Decimal] = Field(
        default=Decimal("100"),
        description="Position size as percentage of capital"
    )
    max_position_size: Optional[Decimal] = Field(
        default=None,
        description="Maximum position size"
    )
    
    # Cost models
    slippage_model: SlippageModel = Field(
        default=SlippageModel.FIXED,
        description="Slippage model"
    )
    slippage_percent: Decimal = Field(
        default=Decimal("0.1"),
        description="Slippage percentage"
    )
    commission_model: CommissionModel = Field(
        default=CommissionModel.FIXED_RATE,
        description="Commission model"
    )
    commission_rate: Decimal = Field(
        default=Decimal("0.1"),
        description="Commission rate"
    )
    
    # Backtest mode
    mode: BacktestMode = Field(
        default=BacktestMode.EVENT_DRIVEN,
        description="Backtest mode"
    )
    
    # Strategy-specific parameters
    strategy_params: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Strategy-specific configuration parameters"
    )
    
    model_config = ConfigDict(use_enum_values=False)


class RunBacktestRequest(BaseModel):
    """Request to run a backtest."""
    
    strategy_id: UUID = Field(..., description="Strategy to test")
    config: BacktestConfigRequest = Field(..., description="Backtest configuration")
    strategy_code: Optional[str] = Field(
        default=None,
        description="Optional strategy code (for custom strategies)"
    )


# Response schemas
class BacktestRunResponse(BaseModel):
    """Backtest run response."""
    
    id: UUID
    user_id: UUID
    strategy_id: UUID
    strategy_name: Optional[str] = None
    symbol: str
    timeframe: str
    start_date: datetime
    end_date: datetime
    initial_capital: Decimal
    status: BacktestStatus
    progress_percent: int
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    error_message: Optional[str]
    final_equity: Optional[Decimal]
    total_trades: Optional[int]
    win_rate: Optional[Decimal]
    total_return: Optional[Decimal]
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)


class PerformanceMetricsResponse(BaseModel):
    """Performance metrics response."""
    
    total_return: Decimal
    annual_return: Decimal
    compound_annual_growth_rate: Decimal
    sharpe_ratio: Decimal
    sortino_ratio: Decimal
    calmar_ratio: Decimal
    max_drawdown: Decimal
    max_drawdown_duration_days: int
    volatility: Decimal
    downside_deviation: Decimal
    win_rate: Decimal
    profit_factor: Decimal
    payoff_ratio: Decimal
    expected_value: Decimal
    total_trades: int
    winning_trades: int
    losing_trades: int
    break_even_trades: int
    average_trade_pnl: Decimal
    average_winning_trade: Decimal
    average_losing_trade: Decimal
    largest_winning_trade: Decimal
    largest_losing_trade: Decimal
    max_consecutive_wins: int
    max_consecutive_losses: int
    average_exposure_percent: Decimal
    max_simultaneous_positions: int
    risk_of_ruin: Decimal
    
    model_config = ConfigDict(from_attributes=True)


class TradeResponse(BaseModel):
    """Trade response."""
    
    symbol: str
    direction: TradeDirection
    entry_price: Decimal
    exit_price: Decimal
    quantity: Decimal
    entry_time: str
    exit_time: str
    duration_seconds: Optional[int]
    gross_pnl: Decimal
    commission: Decimal
    slippage: Decimal
    net_pnl: Decimal
    pnl_percent: Decimal
    mae: Optional[Decimal]
    mfe: Optional[Decimal]
    is_winner: bool
    
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)


class EquityCurvePointResponse(BaseModel):
    """Equity curve point response."""
    
    timestamp: str
    equity: Decimal
    drawdown_percent: Decimal
    return_percent: Decimal
    
    model_config = ConfigDict(from_attributes=True)


class BacktestResultsResponse(BaseModel):
    """Detailed backtest results response."""
    
    backtest_run: BacktestRunResponse
    initial_capital: Decimal
    final_equity: Decimal
    peak_equity: Decimal
    total_trades: int
    performance_metrics: PerformanceMetricsResponse
    equity_curve: List[EquityCurvePointResponse]
    trades: List[TradeResponse]
    
    model_config = ConfigDict(from_attributes=True)


class BacktestListResponse(BaseModel):
    """List of backtests response."""
    
    backtests: List[BacktestRunResponse]
    total: int
    limit: int
    offset: int


class BacktestStatusResponse(BaseModel):
    """Backtest status response."""
    
    id: UUID
    status: BacktestStatus
    progress_percent: int
    message: Optional[str]
    
    model_config = ConfigDict(use_enum_values=True)
