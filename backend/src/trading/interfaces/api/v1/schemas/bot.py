"""Bot API schemas."""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
import uuid


class BotConfigurationRequest(BaseModel):
    """Bot configuration request."""
    bot_type: str = Field(..., description="Bot type (GRID, DCA, MOMENTUM, MEAN_REVERSION, ARBITRAGE, CUSTOM)")
    symbol: str = Field(..., min_length=1, description="Trading symbol (e.g., BTCUSDT)")
    exchange_connection_id: uuid.UUID = Field(..., description="Exchange connection ID")
    
    max_position_size: float = Field(..., gt=0, description="Maximum position size in quote currency")
    max_open_orders: int = Field(..., gt=0, description="Maximum concurrent orders")
    leverage: int = Field(..., ge=1, le=125, description="Leverage (1-125)")
    
    strategy_params: Dict[str, Any] = Field(default_factory=dict, description="Strategy-specific parameters")
    
    stop_loss_pct: Optional[float] = Field(None, gt=0, lt=100, description="Stop loss percentage")
    take_profit_pct: Optional[float] = Field(None, gt=0, lt=1000, description="Take profit percentage")
    max_daily_loss: Optional[float] = Field(None, gt=0, description="Maximum daily loss")


class CreateBotRequest(BaseModel):
    """Create bot request."""
    name: str = Field(..., min_length=1, max_length=100, description="Bot name")
    description: Optional[str] = Field(None, max_length=500, description="Bot description")
    configuration: BotConfigurationRequest


class UpdateBotRequest(BaseModel):
    """Update bot request."""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Bot name")
    description: Optional[str] = Field(None, max_length=500, description="Bot description")
    configuration: Optional[BotConfigurationRequest] = None


class BotMetricsResponse(BaseModel):
    """Bot metrics response."""
    total_trades: int
    winning_trades: int
    losing_trades: int
    total_profit: float
    total_loss: float
    net_profit: float
    win_rate: float
    avg_profit: float
    avg_loss: float
    max_drawdown: float
    profit_factor: float
    sharpe_ratio: Optional[float] = None


class BotConfigurationResponse(BaseModel):
    """Bot configuration response."""
    bot_type: str
    symbol: str
    exchange_connection_id: uuid.UUID
    max_position_size: float
    max_open_orders: int
    leverage: int
    strategy_params: Dict[str, Any]
    stop_loss_pct: Optional[float] = None
    take_profit_pct: Optional[float] = None
    max_daily_loss: Optional[float] = None


class BotResponse(BaseModel):
    """Bot response."""
    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    description: Optional[str] = None
    configuration: BotConfigurationResponse
    status: str
    is_active: bool
    metrics: BotMetricsResponse
    started_at: Optional[datetime] = None
    stopped_at: Optional[datetime] = None
    last_trade_at: Optional[datetime] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class BotListResponse(BaseModel):
    """Bot list response."""
    bots: list[BotResponse]
    total: int


class BotActionResponse(BaseModel):
    """Bot action response (start/stop/pause)."""
    success: bool
    message: str
    bot: BotResponse


__all__ = [
    "BotConfigurationRequest",
    "CreateBotRequest",
    "UpdateBotRequest",
    "BotMetricsResponse",
    "BotConfigurationResponse",
    "BotResponse",
    "BotListResponse",
    "BotActionResponse",
]
