from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from datetime import datetime

from ......domain.risk import IRiskLimitRepository, RiskLimit, RiskLimitType, RiskThreshold, LimitViolation
from ....models.risk_models import RiskLimitModel


class SqlAlchemyRiskLimitRepository(IRiskLimitRepository):
    """SQLAlchemy implementation of IRiskLimitRepository."""
    
    def __init__(self, session: AsyncSession):
        self._session = session
    
    async def save(self, risk_limit: RiskLimit) -> RiskLimit:
        """Save a risk limit."""
        model = self._to_model(risk_limit)
        self._session.add(model)
        await self._session.commit()
        await self._session.refresh(model)
        return self._to_entity(model)
    
    async def find_by_id(self, limit_id: UUID) -> Optional[RiskLimit]:
        """Find risk limit by ID."""
        stmt = select(RiskLimitModel).where(RiskLimitModel.id == limit_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None
    
    async def find_by_user(self, user_id: UUID) -> List[RiskLimit]:
        """Find all risk limits for a user."""
        stmt = select(RiskLimitModel).where(RiskLimitModel.user_id == user_id)
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [self._to_entity(model) for model in models]
    
    async def find_by_user_and_type(self, user_id: UUID, limit_type: RiskLimitType) -> List[RiskLimit]:
        """Find risk limits by user and type."""
        stmt = select(RiskLimitModel).where(
            and_(
                RiskLimitModel.user_id == user_id,
                RiskLimitModel.limit_type == limit_type.value
            )
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [self._to_entity(model) for model in models]
    
    async def find_by_user_and_symbol(self, user_id: UUID, symbol: str) -> List[RiskLimit]:
        """Find risk limits by user and symbol."""
        stmt = select(RiskLimitModel).where(
            and_(
                RiskLimitModel.user_id == user_id,
                RiskLimitModel.symbol == symbol
            )
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [self._to_entity(model) for model in models]
    
    async def find_enabled_by_user(self, user_id: UUID) -> List[RiskLimit]:
        """Find all enabled risk limits for a user."""
        stmt = select(RiskLimitModel).where(
            and_(
                RiskLimitModel.user_id == user_id,
                RiskLimitModel.enabled == True
            )
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [self._to_entity(model) for model in models]
    
    async def update(self, risk_limit: RiskLimit) -> RiskLimit:
        """Update a risk limit."""
        stmt = select(RiskLimitModel).where(RiskLimitModel.id == risk_limit.id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        
        if not model:
            raise ValueError(f"Risk limit with ID {risk_limit.id} not found")
        
        # Update model fields
        model.limit_value = risk_limit.limit_value
        model.enabled = risk_limit.enabled
        model.warning_threshold = risk_limit.threshold.warning_threshold
        model.critical_threshold = risk_limit.threshold.critical_threshold
        model.violations_data = [self._violation_to_dict(v) for v in risk_limit.violations]
        model.updated_at = risk_limit.updated_at
        
        await self._session.commit()
        await self._session.refresh(model)
        return self._to_entity(model)
    
    async def delete(self, limit_id: UUID) -> bool:
        """Delete a risk limit."""
        stmt = select(RiskLimitModel).where(RiskLimitModel.id == limit_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        
        if not model:
            return False
        
        await self._session.delete(model)
        await self._session.commit()
        return True
    
    def _to_model(self, risk_limit: RiskLimit) -> RiskLimitModel:
        """Convert domain entity to SQLAlchemy model."""
        return RiskLimitModel(
            id=risk_limit.id,
            user_id=risk_limit.user_id,
            limit_type=risk_limit.limit_type.value,
            limit_value=risk_limit.limit_value,
            symbol=risk_limit.symbol,
            enabled=risk_limit.enabled,
            warning_threshold=risk_limit.threshold.warning_threshold,
            critical_threshold=risk_limit.threshold.critical_threshold,
            violations_data=[self._violation_to_dict(v) for v in risk_limit.violations],
            created_at=risk_limit.created_at,
            updated_at=risk_limit.updated_at
        )
    
    def _to_entity(self, model: RiskLimitModel) -> RiskLimit:
        """Convert SQLAlchemy model to domain entity."""
        threshold = RiskThreshold(
            warning_threshold=model.warning_threshold,
            critical_threshold=model.critical_threshold
        )
        
        violations = [self._dict_to_violation(v) for v in (model.violations_data or [])]
        
        return RiskLimit(
            id=model.id,
            user_id=model.user_id,
            limit_type=RiskLimitType(model.limit_type),
            limit_value=model.limit_value,
            symbol=model.symbol,
            enabled=model.enabled,
            threshold=threshold,
            created_at=model.created_at,
            updated_at=model.updated_at,
            violations=violations
        )
    
    def _violation_to_dict(self, violation: LimitViolation) -> dict:
        """Convert LimitViolation to dictionary for JSON storage."""
        return {
            "limit_type": violation.limit_type,
            "current_value": str(violation.current_value),
            "limit_value": str(violation.limit_value),
            "violation_percentage": str(violation.violation_percentage),
            "symbol": violation.symbol
        }
    
    def _dict_to_violation(self, data: dict) -> LimitViolation:
        """Convert dictionary to LimitViolation."""
        from decimal import Decimal
        
        return LimitViolation(
            limit_type=data["limit_type"],
            current_value=Decimal(data["current_value"]),
            limit_value=Decimal(data["limit_value"]),
            violation_percentage=Decimal(data["violation_percentage"]),
            symbol=data.get("symbol")
        )