from pydantic import BaseModel, Field, ConfigDict
from decimal import Decimal
from typing import Optional, List
from datetime import datetime
from uuid import UUID

from ....domain.risk.enums import RiskLimitType, RiskStatus, AlertType


# Request Models
class CreateRiskLimitRequest(BaseModel):
    """Request to create a new risk limit."""
    model_config = ConfigDict(json_encoders={Decimal: lambda v: str(v)})
    
    limit_type: RiskLimitType
    limit_value: Decimal = Field(..., gt=0, description="Limit value must be positive")
    symbol: Optional[str] = Field(None, description="Symbol for symbol-specific limits, None for global")
    warning_threshold: Decimal = Field(Decimal('80.0'), ge=0, le=100, description="Warning threshold percentage")
    critical_threshold: Decimal = Field(Decimal('95.0'), ge=0, le=100, description="Critical threshold percentage")


class UpdateRiskLimitRequest(BaseModel):
    """Request to update an existing risk limit."""
    model_config = ConfigDict(json_encoders={Decimal: lambda v: str(v)})
    
    limit_value: Optional[Decimal] = Field(None, gt=0, description="New limit value")
    enabled: Optional[bool] = Field(None, description="Enable or disable the limit")
    warning_threshold: Optional[Decimal] = Field(None, ge=0, le=100, description="Warning threshold percentage")
    critical_threshold: Optional[Decimal] = Field(None, ge=0, le=100, description="Critical threshold percentage")


class MonitorRiskRequest(BaseModel):
    """Request to monitor risk for current metrics."""
    model_config = ConfigDict(json_encoders={Decimal: lambda v: str(v)})
    
    current_equity: Decimal
    daily_pnl: Decimal
    unrealized_pnl: Decimal
    realized_pnl: Decimal
    drawdown_percentage: Decimal
    margin_ratio: Decimal
    exposure_percentage: Decimal
    symbol: Optional[str] = None


# Response Models
class RiskThresholdResponse(BaseModel):
    """Response model for risk thresholds."""
    model_config = ConfigDict(json_encoders={Decimal: lambda v: str(v)})
    
    warning_threshold: Decimal
    critical_threshold: Decimal


class LimitViolationResponse(BaseModel):
    """Response model for limit violations."""
    model_config = ConfigDict(json_encoders={Decimal: lambda v: str(v)})
    
    limit_type: str
    current_value: Decimal
    limit_value: Decimal
    violation_percentage: Decimal
    symbol: Optional[str]


class RiskLimitResponse(BaseModel):
    """Response model for risk limits."""
    model_config = ConfigDict(json_encoders={Decimal: lambda v: str(v), datetime: lambda v: v.isoformat()})
    
    id: UUID
    user_id: UUID
    limit_type: RiskLimitType
    limit_value: Decimal
    symbol: Optional[str]
    enabled: bool
    threshold: RiskThresholdResponse
    violations_count: int
    created_at: datetime
    updated_at: datetime


class RiskAlertResponse(BaseModel):
    """Response model for risk alerts."""
    model_config = ConfigDict(json_encoders={Decimal: lambda v: str(v), datetime: lambda v: v.isoformat()})
    
    id: UUID
    user_id: UUID
    risk_limit_id: UUID
    alert_type: str
    message: str
    severity: RiskStatus
    symbol: Optional[str]
    current_value: Decimal
    limit_value: Decimal
    violation_percentage: Decimal
    acknowledged: bool
    created_at: datetime
    acknowledged_at: Optional[datetime]


class RiskMetricsResponse(BaseModel):
    """Response model for current risk metrics."""
    model_config = ConfigDict(json_encoders={Decimal: lambda v: str(v)})
    
    current_equity: Decimal
    daily_pnl: Decimal
    unrealized_pnl: Decimal
    realized_pnl: Decimal
    total_pnl: Decimal
    drawdown_percentage: Decimal
    margin_ratio: Decimal
    exposure_percentage: Decimal
    equity_at_risk: Decimal