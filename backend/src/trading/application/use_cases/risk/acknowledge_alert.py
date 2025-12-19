from uuid import UUID

from ....domain.risk import RiskAlert, IRiskAlertRepository


class AcknowledgeRiskAlertUseCase:
    """Use case for acknowledging risk alerts."""
    
    def __init__(self, repository: IRiskAlertRepository):
        self._repository = repository
    
    async def execute(self, alert_id: UUID, user_id: UUID) -> RiskAlert:
        """Acknowledge a risk alert."""
        # Get the alert
        alert = await self._repository.find_by_id(alert_id)
        if not alert:
            raise ValueError(f"Risk alert with ID {alert_id} not found")
        
        # Check ownership
        if alert.user_id != user_id:
            raise ValueError("Not authorized to acknowledge this alert")
        
        # Acknowledge the alert
        alert.acknowledge()
        
        # Save changes
        return await self._repository.update(alert)