from dataclasses import dataclass
from decimal import Decimal
from typing import Optional
from uuid import UUID

from ....domain.risk import (
    RiskLimit, 
    RiskLimitType, 
    RiskThreshold, 
    IRiskLimitRepository,
    RiskLimitCreatedEvent
)


@dataclass
class CreateRiskLimitRequest:
    """Request to create a new risk limit."""
    user_id: UUID
    limit_type: RiskLimitType
    limit_value: Decimal
    symbol: Optional[str] = None
    warning_threshold: Decimal = Decimal('80.0')
    critical_threshold: Decimal = Decimal('95.0')


class CreateRiskLimitUseCase:
    """Use case for creating new risk limits."""
    
    def __init__(self, repository: IRiskLimitRepository):
        self._repository = repository
    
    async def execute(self, request: CreateRiskLimitRequest) -> RiskLimit:
        """Create a new risk limit."""
        from datetime import datetime
        import uuid
        
        # Validate request
        if request.limit_value <= 0:
            raise ValueError("Limit value must be positive")
        
        # Check if limit already exists for this user/type/symbol combination
        existing_limits = await self._repository.find_by_user_and_type(
            request.user_id, request.limit_type
        )
        
        if request.symbol:
            # Check for symbol-specific duplicate
            for limit in existing_limits:
                if limit.symbol == request.symbol:
                    raise ValueError(f"Risk limit already exists for {request.symbol} and type {request.limit_type}")
        else:
            # Check for global duplicate
            for limit in existing_limits:
                if limit.symbol is None:
                    raise ValueError(f"Global risk limit already exists for type {request.limit_type}")
        
        # Create threshold
        threshold = RiskThreshold(
            warning_threshold=request.warning_threshold,
            critical_threshold=request.critical_threshold
        )
        
        # Create risk limit
        risk_limit = RiskLimit(
            id=uuid.uuid4(),
            user_id=request.user_id,
            limit_type=request.limit_type,
            limit_value=request.limit_value,
            symbol=request.symbol,
            enabled=True,
            threshold=threshold,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Save to repository
        saved_limit = await self._repository.save(risk_limit)
        
        # TODO: Publish domain event
        # event = RiskLimitCreatedEvent(
        #     user_id=request.user_id,
        #     risk_limit_id=saved_limit.id,
        #     limit_type=request.limit_type.value,
        #     limit_value=request.limit_value,
        #     symbol=request.symbol,
        #     created_at=datetime.utcnow()
        # )
        
        return saved_limit