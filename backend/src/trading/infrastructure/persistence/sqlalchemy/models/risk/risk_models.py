from sqlalchemy import Column, String, Boolean, DECIMAL, DateTime, ForeignKey, Integer, Text, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from ..base import BaseModel

# Cross-database JSON type (JSONB for PostgreSQL, JSON for SQLite)
JSONType = JSON().with_variant(JSONB(), "postgresql")


class RiskLimitModel(BaseModel):
    """SQLAlchemy model for RiskLimit entity."""
    
    __tablename__ = "risk_limits"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    limit_type = Column(String(50), nullable=False, index=True)
    limit_value = Column(DECIMAL(20, 8), nullable=False)
    symbol = Column(String(20), nullable=True, index=True)
    enabled = Column(Boolean, nullable=False, default=True, index=True)
    warning_threshold = Column(DECIMAL(5, 2), nullable=False, default=80.0)
    critical_threshold = Column(DECIMAL(5, 2), nullable=False, default=95.0)
    violations_data = Column(JSONType, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    user = relationship("UserModel", back_populates="risk_limits")
    alerts = relationship("RiskAlertModel", back_populates="risk_limit", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<RiskLimit(id={self.id}, user_id={self.user_id}, type={self.limit_type}, value={self.limit_value})>"


class RiskAlertModel(BaseModel):
    """SQLAlchemy model for RiskAlert entity."""
    
    __tablename__ = "risk_alerts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    risk_limit_id = Column(UUID(as_uuid=True), ForeignKey("risk_limits.id"), nullable=False, index=True)
    alert_type = Column(String(100), nullable=False, index=True)
    message = Column(Text, nullable=False)
    severity = Column(String(20), nullable=False, index=True)
    symbol = Column(String(20), nullable=True, index=True)
    current_value = Column(DECIMAL(20, 8), nullable=False)
    limit_value = Column(DECIMAL(20, 8), nullable=False)
    violation_percentage = Column(DECIMAL(6, 2), nullable=False)
    acknowledged = Column(Boolean, nullable=False, default=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("UserModel", back_populates="risk_alerts")
    risk_limit = relationship("RiskLimitModel", back_populates="alerts")
    
    def __repr__(self):
        return f"<RiskAlert(id={self.id}, user_id={self.user_id}, type={self.alert_type}, severity={self.severity})>"