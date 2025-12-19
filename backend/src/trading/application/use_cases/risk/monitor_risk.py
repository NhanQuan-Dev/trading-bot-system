from dataclasses import dataclass
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from ....domain.risk import (
    RiskLimit, 
    RiskAlert,
    IRiskLimitRepository, 
    IRiskAlertRepository,
    RiskMetrics,
    LimitViolation,
    RiskStatus,
    RiskLimitViolatedEvent,
    RiskAlertCreatedEvent,
    CriticalRiskBreachEvent
)


@dataclass
class MonitorRiskRequest:
    """Request to monitor risk for a user."""
    user_id: UUID
    risk_metrics: RiskMetrics
    symbol: Optional[str] = None


class MonitorRiskUseCase:
    """Use case for monitoring risk limits and creating alerts."""
    
    def __init__(
        self, 
        risk_limit_repository: IRiskLimitRepository,
        risk_alert_repository: IRiskAlertRepository
    ):
        self._risk_limit_repository = risk_limit_repository
        self._risk_alert_repository = risk_alert_repository
    
    async def execute(self, request: MonitorRiskRequest) -> List[RiskAlert]:
        """Monitor risk and create alerts for violations."""
        from datetime import datetime
        import uuid
        from ....domain.risk.enums import RiskLimitType, AlertType
        
        alerts = []
        
        # Get enabled risk limits for the user
        if request.symbol:
            # Get both symbol-specific and global limits
            symbol_limits = await self._risk_limit_repository.find_by_user_and_symbol(
                request.user_id, request.symbol
            )
            global_limits = []
            all_limits = await self._risk_limit_repository.find_enabled_by_user(request.user_id)
            for limit in all_limits:
                if limit.symbol is None:
                    global_limits.append(limit)
            
            risk_limits = symbol_limits + global_limits
        else:
            risk_limits = await self._risk_limit_repository.find_enabled_by_user(request.user_id)
        
        # Check each limit against current metrics
        for risk_limit in risk_limits:
            current_value = self._get_current_value_for_limit(
                risk_limit, request.risk_metrics
            )
            
            if current_value is None:
                continue
            
            # Check for violation
            violation = risk_limit.check_violation(current_value)
            if violation:
                # Create alert
                alert = await self._create_alert(
                    request.user_id,
                    risk_limit,
                    violation,
                    request.symbol
                )
                alerts.append(alert)
        
        return alerts
    
    def _get_current_value_for_limit(
        self, 
        risk_limit: RiskLimit, 
        metrics: RiskMetrics
    ) -> Optional[Decimal]:
        """Get current value based on limit type."""
        from ....domain.risk.enums import RiskLimitType
        
        if risk_limit.limit_type == RiskLimitType.DAILY_LOSS:
            return abs(metrics.daily_pnl) if metrics.daily_pnl < 0 else Decimal('0')
        elif risk_limit.limit_type == RiskLimitType.DRAWDOWN:
            return metrics.drawdown_percentage
        elif risk_limit.limit_type == RiskLimitType.EXPOSURE:
            return metrics.exposure_percentage
        elif risk_limit.limit_type == RiskLimitType.LEVERAGE:
            return metrics.margin_ratio
        elif risk_limit.limit_type == RiskLimitType.POSITION_SIZE:
            return metrics.equity_at_risk
        
        return None
    
    async def _create_alert(
        self,
        user_id: UUID,
        risk_limit: RiskLimit,
        violation: LimitViolation,
        symbol: Optional[str]
    ) -> RiskAlert:
        """Create a risk alert for the violation."""
        import uuid
        from datetime import datetime
        from ....domain.risk.enums import AlertType
        
        # Determine alert type and message
        alert_type = self._get_alert_type(risk_limit.limit_type.value, violation)
        message = self._create_alert_message(risk_limit, violation, symbol)
        
        # Determine severity
        if violation.is_breached:
            severity = RiskStatus.BREACHED
        elif violation.is_critical:
            severity = RiskStatus.CRITICAL
        elif violation.is_warning:
            severity = RiskStatus.WARNING
        else:
            severity = RiskStatus.NORMAL
        
        # Create alert
        alert = RiskAlert(
            id=uuid.uuid4(),
            user_id=user_id,
            risk_limit_id=risk_limit.id,
            alert_type=alert_type,
            message=message,
            severity=severity,
            symbol=symbol,
            current_value=violation.current_value,
            limit_value=violation.limit_value,
            violation_percentage=violation.violation_percentage,
            acknowledged=False,
            created_at=datetime.utcnow()
        )
        
        # Save alert
        saved_alert = await self._risk_alert_repository.save(alert)
        
        # TODO: Publish domain events
        # if violation.is_critical:
        #     event = CriticalRiskBreachEvent(...)
        # else:
        #     event = RiskAlertCreatedEvent(...)
        
        return saved_alert
    
    def _get_alert_type(self, limit_type: str, violation: LimitViolation) -> str:
        """Get alert type based on limit type and violation severity."""
        from ....domain.risk.enums import AlertType
        
        if violation.is_breached:
            if limit_type == "DAILY_LOSS":
                return AlertType.DAILY_LOSS_LIMIT_EXCEEDED.value
            elif limit_type == "POSITION_SIZE":
                return AlertType.POSITION_LIMIT_EXCEEDED.value
            elif limit_type == "DRAWDOWN":
                return AlertType.DRAWDOWN_LIMIT_EXCEEDED.value
        else:
            if limit_type == "DAILY_LOSS":
                return AlertType.DAILY_LOSS_LIMIT_APPROACHED.value
            elif limit_type == "POSITION_SIZE":
                return AlertType.POSITION_LIMIT_APPROACHED.value
            elif limit_type == "DRAWDOWN":
                return AlertType.DRAWDOWN_LIMIT_APPROACHED.value
        
        return "RISK_LIMIT_VIOLATION"
    
    def _create_alert_message(
        self, 
        risk_limit: RiskLimit, 
        violation: LimitViolation,
        symbol: Optional[str]
    ) -> str:
        """Create a human-readable alert message."""
        symbol_text = f" for {symbol}" if symbol else ""
        
        if violation.is_breached:
            return (f"{risk_limit.limit_type.value} limit exceeded{symbol_text}. "
                   f"Current: {violation.current_value}, "
                   f"Limit: {violation.limit_value} "
                   f"({violation.violation_percentage:.1f}%)")
        else:
            return (f"{risk_limit.limit_type.value} limit approached{symbol_text}. "
                   f"Current: {violation.current_value}, "
                   f"Limit: {violation.limit_value} "
                   f"({violation.violation_percentage:.1f}%)")