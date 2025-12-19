from dataclasses import dataclass
from decimal import Decimal
from typing import Optional
from uuid import UUID

from ....domain.risk import RiskLimit, IRiskLimitRepository, RiskThreshold


@dataclass
class UpdateRiskLimitRequest:
    """Request to update a risk limit."""
    limit_id: UUID
    user_id: UUID
    limit_value: Optional[Decimal] = None
    enabled: Optional[bool] = None
    warning_threshold: Optional[Decimal] = None
    critical_threshold: Optional[Decimal] = None


class UpdateRiskLimitUseCase:
    """Use case for updating risk limits."""
    
    def __init__(self, repository: IRiskLimitRepository):
        self._repository = repository
    
    async def execute(self, request: UpdateRiskLimitRequest) -> RiskLimit:
        """Update an existing risk limit."""
        # Get existing limit
        existing_limit = await self._repository.find_by_id(request.limit_id)
        if not existing_limit:
            raise ValueError(f"Risk limit with ID {request.limit_id} not found")
        
        # Check ownership
        if existing_limit.user_id != request.user_id:
            raise ValueError("Not authorized to update this risk limit")
        
        # Update limit value if provided
        if request.limit_value is not None:
            existing_limit.update_limit(request.limit_value)
        
        # Update enabled status if provided
        if request.enabled is not None:
            if request.enabled:
                existing_limit.enable()
            else:
                existing_limit.disable()
        
        # Update thresholds if provided
        if request.warning_threshold is not None or request.critical_threshold is not None:
            warning = request.warning_threshold or existing_limit.threshold.warning_threshold
            critical = request.critical_threshold or existing_limit.threshold.critical_threshold
            
            new_threshold = RiskThreshold(
                warning_threshold=warning,
                critical_threshold=critical
            )
            existing_limit.update_threshold(new_threshold)
        
        # Save changes
        return await self._repository.update(existing_limit)