from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional

from ....application.use_cases.risk import (
    CreateRiskLimitUseCase,
    GetRiskLimitsUseCase,
    UpdateRiskLimitUseCase,
    DeleteRiskLimitUseCase,
    MonitorRiskUseCase,
    GetRiskAlertsUseCase,
    AcknowledgeRiskAlertUseCase,
    CreateRiskLimitRequest as CreateRiskLimitUseCaseRequest,
    UpdateRiskLimitRequest as UpdateRiskLimitUseCaseRequest,
    MonitorRiskRequest as MonitorRiskUseCaseRequest
)
from ....domain.risk import RiskMetrics
from ....interfaces.dependencies.auth import get_current_user_id
from ....interfaces.dependencies.providers import (
    get_create_risk_limit_use_case,
    get_get_risk_limits_use_case,
    get_update_risk_limit_use_case,
    get_delete_risk_limit_use_case,
    get_monitor_risk_use_case,
    get_get_risk_alerts_use_case,
    get_acknowledge_risk_alert_use_case
)
from .schemas import (
    CreateRiskLimitRequest,
    UpdateRiskLimitRequest,
    MonitorRiskRequest,
    RiskLimitResponse,
    RiskAlertResponse,
    RiskThresholdResponse,
    RiskMetricsResponse
)
from uuid import UUID


router = APIRouter(prefix="/risk", tags=["Risk Management"])


def _to_risk_limit_response(risk_limit) -> RiskLimitResponse:
    """Convert domain RiskLimit to response model."""
    return RiskLimitResponse(
        id=risk_limit.id,
        user_id=risk_limit.user_id,
        limit_type=risk_limit.limit_type,
        limit_value=risk_limit.limit_value,
        symbol=risk_limit.symbol,
        enabled=risk_limit.enabled,
        threshold=RiskThresholdResponse(
            warning_threshold=risk_limit.threshold.warning_threshold,
            critical_threshold=risk_limit.threshold.critical_threshold
        ),
        violations_count=len(risk_limit.violations),
        created_at=risk_limit.created_at,
        updated_at=risk_limit.updated_at
    )


def _to_risk_alert_response(alert) -> RiskAlertResponse:
    """Convert domain RiskAlert to response model."""
    return RiskAlertResponse(
        id=alert.id,
        user_id=alert.user_id,
        risk_limit_id=alert.risk_limit_id,
        alert_type=alert.alert_type,
        message=alert.message,
        severity=alert.severity,
        symbol=alert.symbol,
        current_value=alert.current_value,
        limit_value=alert.limit_value,
        violation_percentage=alert.violation_percentage,
        acknowledged=alert.acknowledged,
        created_at=alert.created_at,
        acknowledged_at=alert.acknowledged_at
    )


# Risk Limits Endpoints
@router.post("/limits", response_model=RiskLimitResponse, status_code=status.HTTP_201_CREATED)
async def create_risk_limit(
    request: CreateRiskLimitRequest,
    user_id: UUID = Depends(get_current_user_id),
    use_case: CreateRiskLimitUseCase = Depends(get_create_risk_limit_use_case)
):
    """Create a new risk limit."""
    try:
        # Convert API request to use case request
        use_case_request = CreateRiskLimitUseCaseRequest(
            user_id=user_id,
            limit_type=request.limit_type,
            limit_value=request.limit_value,
            symbol=request.symbol,
            warning_threshold=request.warning_threshold,
            critical_threshold=request.critical_threshold
        )
        
        # Execute use case
        risk_limit = await use_case.execute(use_case_request)
        
        # Convert to response
        return _to_risk_limit_response(risk_limit)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create risk limit"
        )


@router.get("/limits", response_model=List[RiskLimitResponse])
async def get_risk_limits(
    symbol: Optional[str] = None,
    enabled_only: bool = False,
    user_id: UUID = Depends(get_current_user_id),
    use_case: GetRiskLimitsUseCase = Depends(get_get_risk_limits_use_case)
):
    """Get risk limits for the current user."""
    try:
        if symbol:
            risk_limits = await use_case.get_by_symbol(user_id, symbol)
        elif enabled_only:
            risk_limits = await use_case.get_enabled_limits(user_id)
        else:
            risk_limits = await use_case.execute(user_id)
        
        return [_to_risk_limit_response(limit) for limit in risk_limits]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve risk limits"
        )


@router.put("/limits/{limit_id}", response_model=RiskLimitResponse)
async def update_risk_limit(
    limit_id: UUID,
    request: UpdateRiskLimitRequest,
    user_id: UUID = Depends(get_current_user_id),
    use_case: UpdateRiskLimitUseCase = Depends(get_update_risk_limit_use_case)
):
    """Update an existing risk limit."""
    try:
        # Convert API request to use case request
        use_case_request = UpdateRiskLimitUseCaseRequest(
            limit_id=limit_id,
            user_id=user_id,
            limit_value=request.limit_value,
            enabled=request.enabled,
            warning_threshold=request.warning_threshold,
            critical_threshold=request.critical_threshold
        )
        
        # Execute use case
        risk_limit = await use_case.execute(use_case_request)
        
        # Convert to response
        return _to_risk_limit_response(risk_limit)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update risk limit"
        )


@router.delete("/limits/{limit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_risk_limit(
    limit_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    use_case: DeleteRiskLimitUseCase = Depends(get_delete_risk_limit_use_case)
):
    """Delete a risk limit."""
    try:
        success = await use_case.execute(limit_id, user_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Risk limit not found"
            )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete risk limit"
        )


# Risk Monitoring Endpoints
@router.post("/monitor", response_model=List[RiskAlertResponse])
async def monitor_risk(
    request: MonitorRiskRequest,
    user_id: UUID = Depends(get_current_user_id),
    use_case: MonitorRiskUseCase = Depends(get_monitor_risk_use_case)
):
    """Monitor current risk metrics and create alerts if needed."""
    try:
        # Convert API request to domain model
        risk_metrics = RiskMetrics(
            current_equity=request.current_equity,
            daily_pnl=request.daily_pnl,
            unrealized_pnl=request.unrealized_pnl,
            realized_pnl=request.realized_pnl,
            drawdown_percentage=request.drawdown_percentage,
            margin_ratio=request.margin_ratio,
            exposure_percentage=request.exposure_percentage
        )
        
        # Create use case request
        use_case_request = MonitorRiskUseCaseRequest(
            user_id=user_id,
            risk_metrics=risk_metrics,
            symbol=request.symbol
        )
        
        # Execute use case
        alerts = await use_case.execute(use_case_request)
        
        # Convert to response
        return [_to_risk_alert_response(alert) for alert in alerts]
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to monitor risk"
        )


# Risk Alerts Endpoints
@router.get("/alerts", response_model=List[RiskAlertResponse])
async def get_risk_alerts(
    unacknowledged_only: bool = False,
    user_id: UUID = Depends(get_current_user_id),
    use_case: GetRiskAlertsUseCase = Depends(get_get_risk_alerts_use_case)
):
    """Get risk alerts for the current user."""
    try:
        if unacknowledged_only:
            alerts = await use_case.get_unacknowledged(user_id)
        else:
            alerts = await use_case.execute(user_id)
        
        return [_to_risk_alert_response(alert) for alert in alerts]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve risk alerts"
        )


@router.post("/alerts/{alert_id}/acknowledge", response_model=RiskAlertResponse)
async def acknowledge_risk_alert(
    alert_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    use_case: AcknowledgeRiskAlertUseCase = Depends(get_acknowledge_risk_alert_use_case)
):
    """Acknowledge a risk alert."""
    try:
        alert = await use_case.execute(alert_id, user_id)
        return _to_risk_alert_response(alert)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to acknowledge risk alert"
        )


# Utility Endpoints  
@router.get("/metrics", response_model=RiskMetricsResponse)
async def calculate_risk_metrics(
    current_equity: float,
    daily_pnl: float,
    unrealized_pnl: float,
    realized_pnl: float,
    drawdown_percentage: float,
    margin_ratio: float,
    exposure_percentage: float
):
    """Calculate risk metrics from provided values."""
    try:
        from decimal import Decimal
        
        # Create risk metrics
        metrics = RiskMetrics(
            current_equity=Decimal(str(current_equity)),
            daily_pnl=Decimal(str(daily_pnl)),
            unrealized_pnl=Decimal(str(unrealized_pnl)),
            realized_pnl=Decimal(str(realized_pnl)),
            drawdown_percentage=Decimal(str(drawdown_percentage)),
            margin_ratio=Decimal(str(margin_ratio)),
            exposure_percentage=Decimal(str(exposure_percentage))
        )
        
        return RiskMetricsResponse(
            current_equity=metrics.current_equity,
            daily_pnl=metrics.daily_pnl,
            unrealized_pnl=metrics.unrealized_pnl,
            realized_pnl=metrics.realized_pnl,
            total_pnl=metrics.total_pnl,
            drawdown_percentage=metrics.drawdown_percentage,
            margin_ratio=metrics.margin_ratio,
            exposure_percentage=metrics.exposure_percentage,
            equity_at_risk=metrics.equity_at_risk
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to calculate risk metrics"
        )