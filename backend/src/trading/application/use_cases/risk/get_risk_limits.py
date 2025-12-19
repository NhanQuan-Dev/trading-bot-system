from typing import List
from uuid import UUID

from ....domain.risk import RiskLimit, IRiskLimitRepository


class GetRiskLimitsUseCase:
    """Use case for retrieving risk limits."""
    
    def __init__(self, repository: IRiskLimitRepository):
        self._repository = repository
    
    async def execute(self, user_id: UUID) -> List[RiskLimit]:
        """Get all risk limits for a user."""
        return await self._repository.find_by_user(user_id)
    
    async def get_enabled_limits(self, user_id: UUID) -> List[RiskLimit]:
        """Get only enabled risk limits for a user."""
        return await self._repository.find_enabled_by_user(user_id)
    
    async def get_by_symbol(self, user_id: UUID, symbol: str) -> List[RiskLimit]:
        """Get risk limits for a specific symbol."""
        return await self._repository.find_by_user_and_symbol(user_id, symbol)