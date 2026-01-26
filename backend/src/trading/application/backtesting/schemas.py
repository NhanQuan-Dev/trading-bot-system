"""Backtesting request/response schemas."""

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict, field_validator
import dataclasses

from ...domain.backtesting import (
    BacktestStatus,
    BacktestMode,
    SlippageModel,
    CommissionModel,
    PositionSizing,
    TradeDirection,
    FillPolicy,
   PricePathAssumption,
)


# Request schemas
class BacktestConfigRequest(BaseModel):
    """Backtest configuration request."""
    
    symbol: str = Field(..., description="Trading symbol")
    timeframe: str = Field(..., description="Candlestick timeframe")
    start_date: datetime = Field(..., description="Backtest start date")
    end_date: datetime = Field(..., description="Backtest end date")
    initial_capital: Decimal = Field(..., description="Initial capital", gt=0)
    
    # Risk Management
    leverage: int = Field(default=1, description="Leverage (1x to 125x)", ge=1, le=125)
    
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
    
    # Advanced Costs
    taker_fee_rate: Decimal = Field(default=Decimal("0.04"), description="Taker Fee %")
    maker_fee_rate: Decimal = Field(default=Decimal("0.02"), description="Maker Fee %")
    funding_rate_daily: Decimal = Field(default=Decimal("0.03"), description="Daily Funding Rate %")
    
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
    
    # Spec-required Phase 1: Fill policy configuration
    fill_policy: str = Field(
        default="optimistic",
        description="DEPRECATED: Use market_fill_policy and limit_fill_policy"
    )
    market_fill_policy: str = Field(
        default="close",
        description="Market order fill price: close | low | high"
    )
    limit_fill_policy: str = Field(
        default="cross",
        description="Limit order fill condition: touch | cross | cross_volume"
    )
    price_path_assumption: str = Field(
        default="neutral",
        description="Conflict Resolution (TP/SL): neutral (SL first) | optimistic (TP first) | realistic (based on open)"
    )
    
    # Spec-required Phase 2: Multi-timeframe settings
    # Spec-required Phase 2: data_timeframe is always 1m (hardcoded), only signal_timeframe is configurable
    signal_timeframe: str = Field(
        default="1m",
        description="Higher timeframe for strategy signals (1m/1h/4h/1d)"
    )
    
    execution_delay_bars: int = Field(
        default=0,
        description="Number of 1m bars to delay signal execution",
        ge=0
    )

    # Spec-required Phase 2: Condition timeframes (Multi-TF support)
    condition_timeframes: Optional[List[str]] = Field(
        default=None,
        description="Timeframes to evaluate strategies conditions (e.g., ['15m', '30m', '1h'])"
    )
    
    # Spec-required Phase 3: Setup-Trigger model
    enable_setup_trigger_model: bool = Field(
        default=False,
        description="Enable Setup-Trigger state machine for HTF setups"
    )
    setup_validity_window_minutes: int = Field(
        default=60,
        description="How long a setup remains valid before expiring"
    )
    
    model_config = ConfigDict(use_enum_values=False)


class RunBacktestRequest(BaseModel):
    """Request to run a backtest."""
    
    strategy_id: UUID = Field(..., description="Strategy to test")
    exchange_connection_id: Optional[UUID] = Field(None, description="Exchange connection to use (deprecated, use exchange_name)")
    exchange_name: Optional[str] = Field(None, description="Exchange name (e.g., BINANCE)")
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
    
    # NEW: Expose leverage for frontend convenience
    leverage: Optional[int] = None
    
    # Exchange connection
    exchange_connection_id: UUID
    exchange_name: Optional[str] = None
    
    symbol: str
    timeframe: str
    start_date: datetime
    end_date: datetime
    initial_capital: Decimal
    status: BacktestStatus
    progress_percent: int
    status_message: Optional[str] = None  # NEW: User-friendly progress message
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    error_message: Optional[str]
    final_equity: Optional[Decimal]
    total_trades: Optional[int]
    win_rate: Optional[Decimal]
    total_return: Optional[Decimal]
    
    # Performance metrics
    profit_factor: Optional[Decimal] = None
    max_drawdown: Optional[Decimal] = None
    sharpe_ratio: Optional[Decimal] = None
    
    # Spec-required: Phase 2-3 config info for frontend display
    signal_timeframe: Optional[str] = None
    fill_policy: Optional[str] = None
    market_fill_policy: Optional[str] = None
    limit_fill_policy: Optional[str] = None
    price_path_assumption: Optional[str] = None
    
    created_at: datetime
    config: Dict[str, Any]
    
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    @field_validator('config', mode='before')
    @classmethod
    def parse_config(cls, v):
        if dataclasses.is_dataclass(v):
            return dataclasses.asdict(v)
        return v


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
    initial_entry_price: Optional[Decimal] = None
    initial_entry_quantity: Optional[Decimal] = None
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
    
    # Detailed Fees
    maker_fee: Optional[Decimal] = Decimal("0")
    taker_fee: Optional[Decimal] = Decimal("0")
    funding_fee: Optional[Decimal] = Decimal("0")
    
    entry_reason: Optional[Dict[str, Any]] = None
    
    # Spec-required: Timeline tracking
    signal_time: Optional[str] = None
    execution_delay_seconds: Optional[float] = None
    
    # Spec-required: Intra-trade metrics
    max_drawdown: Optional[Decimal] = None
    max_runup: Optional[Decimal] = None
    
    # Spec-required: Fill metadata
    fill_policy_used: Optional[str] = None
    fill_conditions_met: Optional[Dict[str, bool]] = None
    
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


class PeriodProfitStats(BaseModel):
    """Profit statistics for a single period type."""
    
    avg_profit: float = Field(..., description="Average profit per period")
    max_profit: float = Field(..., description="Maximum profit in a period")
    min_profit: float = Field(..., description="Minimum profit in a period")


class PeriodTradeStats(BaseModel):
    """Trade count statistics for a single period type."""
    
    avg_trades: float = Field(..., description="Average trades per period")
    max_trades: int = Field(..., description="Maximum trades in a period")
    min_trades: int = Field(..., description="Minimum trades in a period")


class BacktestPeriodStatsResponse(BaseModel):
    """Period-based statistics for backtest."""
    
    # Profit stats per period
    profit_day: PeriodProfitStats
    profit_week: PeriodProfitStats
    profit_month: PeriodProfitStats
    profit_year: PeriodProfitStats
    
    # Trade stats per period
    trades_day: PeriodTradeStats
    trades_week: PeriodTradeStats
    trades_month: PeriodTradeStats
    trades_year: PeriodTradeStats

