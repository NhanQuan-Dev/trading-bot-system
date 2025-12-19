from uuid import UUID

from ....domain.risk import IRiskLimitRepository


class DeleteRiskLimitUseCase:
    """Use case for deleting risk limits."""
    
    def __init__(self, repository: IRiskLimitRepository):
        self._repository = repository
    
    async def execute(self, limit_id: UUID, user_id: UUID) -> bool:
        """Delete a risk limit."""
        # Check if limit exists and user owns it
        existing_limit = await self._repository.find_by_id(limit_id)
        if not existing_limit:
            raise ValueError(f"Risk limit with ID {limit_id} not found")
        
        if existing_limit.user_id != user_id:
            raise ValueError("Not authorized to delete this risk limit")
        
        # Delete the limit
        return await self._repository.delete(limit_id)