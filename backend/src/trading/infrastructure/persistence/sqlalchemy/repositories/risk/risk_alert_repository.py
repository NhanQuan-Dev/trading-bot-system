from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from datetime import datetime

from ......domain.risk import IRiskAlertRepository, RiskAlert, RiskStatus
from ....models.risk_models import RiskAlertModel


class SqlAlchemyRiskAlertRepository(IRiskAlertRepository):
    """SQLAlchemy implementation of IRiskAlertRepository."""
    
    def __init__(self, session: AsyncSession):
        self._session = session
    
    async def save(self, alert: RiskAlert) -> RiskAlert:
        """Save a risk alert."""
        model = self._to_model(alert)
        self._session.add(model)
        await self._session.commit()
        await self._session.refresh(model)
        return self._to_entity(model)
    
    async def find_by_id(self, alert_id: UUID) -> Optional[RiskAlert]:
        """Find risk alert by ID."""
        stmt = select(RiskAlertModel).where(RiskAlertModel.id == alert_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None
    
    async def find_by_user(self, user_id: UUID) -> List[RiskAlert]:
        """Find all risk alerts for a user."""
        stmt = select(RiskAlertModel).where(
            RiskAlertModel.user_id == user_id
        ).order_by(RiskAlertModel.created_at.desc())
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [self._to_entity(model) for model in models]
    
    async def find_unacknowledged_by_user(self, user_id: UUID) -> List[RiskAlert]:
        """Find unacknowledged risk alerts for a user."""
        stmt = select(RiskAlertModel).where(
            and_(
                RiskAlertModel.user_id == user_id,
                RiskAlertModel.acknowledged == False
            )
        ).order_by(RiskAlertModel.created_at.desc())
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [self._to_entity(model) for model in models]
    
    async def find_by_risk_limit(self, risk_limit_id: UUID) -> List[RiskAlert]:
        """Find alerts for a specific risk limit."""
        stmt = select(RiskAlertModel).where(
            RiskAlertModel.risk_limit_id == risk_limit_id
        ).order_by(RiskAlertModel.created_at.desc())
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [self._to_entity(model) for model in models]
    
    async def update(self, alert: RiskAlert) -> RiskAlert:
        """Update a risk alert."""
        stmt = select(RiskAlertModel).where(RiskAlertModel.id == alert.id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        
        if not model:
            raise ValueError(f"Risk alert with ID {alert.id} not found")
        
        # Update model fields
        model.acknowledged = alert.acknowledged
        model.acknowledged_at = alert.acknowledged_at
        
        await self._session.commit()
        await self._session.refresh(model)
        return self._to_entity(model)
    
    async def delete(self, alert_id: UUID) -> bool:
        """Delete a risk alert."""
        stmt = select(RiskAlertModel).where(RiskAlertModel.id == alert_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        
        if not model:
            return False
        
        await self._session.delete(model)
        await self._session.commit()
        return True
    
    def _to_model(self, alert: RiskAlert) -> RiskAlertModel:
        """Convert domain entity to SQLAlchemy model."""
        return RiskAlertModel(
            id=alert.id,
            user_id=alert.user_id,
            risk_limit_id=alert.risk_limit_id,
            alert_type=alert.alert_type,
            message=alert.message,
            severity=alert.severity.value,
            symbol=alert.symbol,
            current_value=alert.current_value,
            limit_value=alert.limit_value,
            violation_percentage=alert.violation_percentage,
            acknowledged=alert.acknowledged,
            created_at=alert.created_at,
            acknowledged_at=alert.acknowledged_at
        )
    
    def _to_entity(self, model: RiskAlertModel) -> RiskAlert:
        """Convert SQLAlchemy model to domain entity."""
        return RiskAlert(
            id=model.id,
            user_id=model.user_id,
            risk_limit_id=model.risk_limit_id,
            alert_type=model.alert_type,
            message=model.message,
            severity=RiskStatus(model.severity),
            symbol=model.symbol,
            current_value=model.current_value,
            limit_value=model.limit_value,
            violation_percentage=model.violation_percentage,
            acknowledged=model.acknowledged,
            created_at=model.created_at,
            acknowledged_at=model.acknowledged_at
        )