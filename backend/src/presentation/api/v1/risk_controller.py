"""
Risk Management Controller for trading platform API.

Provides REST endpoints for risk monitoring, exposure analysis, 
risk limits management, and emergency controls.
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from trading.infrastructure.persistence.database import get_db
from trading.interfaces.dependencies.auth import get_current_user
from trading.infrastructure.persistence.models.core_models import UserModel
from application.services.risk_monitoring_service import (
    RiskMonitoringService,
    RiskOverview,
    ExposureBreakdown,
    RiskLimit,
    RiskAlert
)


# Request/Response models
class UpdateRiskLimitsRequest(BaseModel):
    """Request model for updating risk limits."""
    position_size_limit: Optional[float] = Field(None, ge=0, description="Maximum position size")
    daily_loss_limit: Optional[float] = Field(None, ge=0, description="Maximum daily loss")
    exposure_limit: Optional[float] = Field(None, ge=0, le=100000000, description="Maximum portfolio exposure")


class EmergencyStopRequest(BaseModel):
    """Request model for emergency stop."""
    reason: str = Field(..., min_length=1, max_length=500, description="Reason for emergency stop")


router = APIRouter(prefix="/api/risk", tags=["risk"])


@router.get("/overview", response_model=RiskOverview)
async def get_risk_overview(
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> RiskOverview:
    """
    Get comprehensive risk dashboard overview.
    
    Returns real-time risk metrics including:
    - Current exposure value
    - Leverage usage
    - Margin level
    - Risk score (1-100 scale)
    - Number of active alerts
    """
    service = RiskMonitoringService(db)
    
    try:
        overview = await service.get_risk_overview(user_id=current_user.id)
        return overview
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get risk overview: {str(e)}")


@router.get("/exposure", response_model=List[ExposureBreakdown])
async def get_exposure_breakdown(
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> List[ExposureBreakdown]:
    """
    Get detailed exposure breakdown by asset.
    
    Returns per-asset exposure analysis including:
    - Exposure value and percentage
    - Risk limits for each asset
    - Risk status (safe/warning/danger)
    
    Sorted by exposure value (highest first).
    """
    service = RiskMonitoringService(db)
    
    try:
        exposure_breakdown = await service.get_exposure_breakdown(user_id=current_user.id)
        return exposure_breakdown
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get exposure breakdown: {str(e)}")


@router.get("/limits", response_model=List[RiskLimit])
async def get_risk_limits(
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> List[RiskLimit]:
    """
    Get user's risk limits configuration.
    
    Returns configured risk limits including:
    - Position size limits
    - Daily loss limits
    - Exposure limits
    - Current values vs limits
    - Risk status for each limit
    """
    service = RiskMonitoringService(db)
    
    try:
        risk_limits = await service.get_risk_limits(user_id=current_user.id)
        return risk_limits
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get risk limits: {str(e)}")


@router.post("/limits", response_model=List[RiskLimit])
async def update_risk_limits(
    request: UpdateRiskLimitsRequest,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> List[RiskLimit]:
    """
    Update user's risk limits configuration.
    
    Allows updating:
    - position_size_limit: Maximum position size
    - daily_loss_limit: Maximum daily loss allowed
    - exposure_limit: Maximum portfolio exposure
    
    Returns updated risk limits configuration.
    """
    service = RiskMonitoringService(db)
    
    # Validate that at least one limit is provided
    if all(v is None for v in [request.position_size_limit, request.daily_loss_limit, request.exposure_limit]):
        raise HTTPException(status_code=400, detail="At least one risk limit must be provided")
    
    try:
        updated_limits = await service.update_risk_limits(
            user_id=current_user.id,
            position_size_limit=request.position_size_limit,
            daily_loss_limit=request.daily_loss_limit,
            exposure_limit=request.exposure_limit
        )
        return updated_limits
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update risk limits: {str(e)}")


@router.get("/alerts", response_model=List[RiskAlert])
async def get_risk_alerts(
    limit: int = Query(50, ge=1, le=100, description="Maximum number of alerts to return"),
    offset: int = Query(0, ge=0, description="Number of alerts to skip"),
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> List[RiskAlert]:
    """
    Get risk alerts history.
    
    Returns paginated list of risk alerts including:
    - Alert type and severity
    - Alert message and timestamp
    - Resolution status and time
    - Whether alert is still active
    
    Ordered by triggered time (most recent first).
    """
    service = RiskMonitoringService(db)
    
    try:
        alerts = await service.get_risk_alerts(
            user_id=current_user.id,
            limit=limit,
            offset=offset
        )
        return alerts
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get risk alerts: {str(e)}")


@router.post("/emergency-stop", response_model=Dict[str, Any])
async def emergency_stop_all_bots(
    request: EmergencyStopRequest,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Emergency stop all bots and close positions.
    
    CRITICAL OPERATION: This will:
    - Stop all running bots immediately
    - Close all open positions (market orders)
    - Create emergency alert record
    - Send notifications (if configured)
    
    Use only in emergency situations when immediate risk reduction is needed.
    
    Returns summary of stopped bots and closed positions.
    """
    service = RiskMonitoringService(db)
    
    try:
        result = await service.emergency_stop_all_bots(
            user_id=current_user.id,
            reason=request.reason
        )
        
        # Log the emergency stop for audit purposes
        # In production, would also send notifications here
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to execute emergency stop: {str(e)}")