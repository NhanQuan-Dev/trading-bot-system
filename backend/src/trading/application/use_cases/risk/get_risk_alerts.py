from typing import List
from uuid import UUID

from ....domain.risk import RiskAlert, IRiskAlertRepository


class GetRiskAlertsUseCase:
    """Use case for retrieving risk alerts."""
    
    def __init__(self, repository: IRiskAlertRepository):
        self._repository = repository
    
    async def execute(self, user_id: UUID) -> List[RiskAlert]:
        """Get all risk alerts for a user."""
        return await self._repository.find_by_user(user_id)
    
    async def get_unacknowledged(self, user_id: UUID) -> List[RiskAlert]:
        """Get unacknowledged risk alerts for a user."""
        return await self._repository.find_unacknowledged_by_user(user_id)