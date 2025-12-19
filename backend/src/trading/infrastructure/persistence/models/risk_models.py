"""SQLAlchemy models for risk management and alerts."""
from sqlalchemy import Column, String, Boolean, DECIMAL, DateTime, ForeignKey, Integer, Text, Index, CheckConstraint, BigInteger, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import TimestampMixin, SoftDeleteMixin, UUIDPrimaryKeyMixin
from ..database import Base

# Cross-database JSON type (JSONB for PostgreSQL, JSON for SQLite)
JSONType = JSON().with_variant(JSONB(), "postgresql")


class RiskLimitModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """SQLAlchemy model for RiskLimit entity."""
    
    __tablename__ = "risk_limits"
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    limit_type = Column(String(50), nullable=False, index=True)
    limit_value = Column(DECIMAL(20, 8), nullable=False)
    symbol = Column(String(20), nullable=True, index=True)
    enabled = Column(Boolean, nullable=False, default=True, index=True)
    warning_threshold = Column(DECIMAL(5, 2), nullable=False, default=80.0)
    critical_threshold = Column(DECIMAL(5, 2), nullable=False, default=95.0)
    violations_data = Column(JSONType, nullable=False, default=list)
    
    # Relationships
    user = relationship("UserModel", back_populates="risk_limits")
    alerts = relationship("RiskAlertModel", back_populates="risk_limit", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<RiskLimit(id={self.id}, user_id={self.user_id}, type={self.limit_type}, value={self.limit_value})>"


class RiskAlertModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """SQLAlchemy model for RiskAlert entity."""
    
    __tablename__ = "risk_alerts"
    
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
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("UserModel", back_populates="risk_alerts")
    risk_limit = relationship("RiskLimitModel", back_populates="alerts")
    
    def __repr__(self):
        return f"<RiskAlert(id={self.id}, user_id={self.user_id}, type={self.alert_type}, severity={self.severity})>"


# Legacy models (kept for backwards compatibility)
class AlertModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Price and condition alert model."""
    
    __tablename__ = "alerts"
    __table_args__ = (
        Index('idx_alerts_user_symbol_status', 'user_id', 'symbol', 'status'),
        Index('idx_alerts_status_created', 'status', 'created_at'),
        CheckConstraint("type IN ('PRICE', 'VOLUME', 'INDICATOR', 'POSITION', 'RISK')", name='ck_alerts_type'),
        CheckConstraint("status IN ('ACTIVE', 'TRIGGERED', 'DISABLED', 'EXPIRED')", name='ck_alerts_status'),
        {'comment': 'User-defined alerts and notifications'}
    )
    
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    symbol = Column(String(20), nullable=True, comment="Symbol to monitor (NULL for account-level)")
    exchange_id = Column(Integer, ForeignKey('exchanges.id', ondelete='RESTRICT'), nullable=True)
    
    type = Column(String(20), nullable=False, comment="Alert type")
    name = Column(String(100), nullable=False, comment="Alert name")
    condition = Column(JSONType, nullable=False, comment="Alert condition (JSON)")
    message = Column(String(500), nullable=True, comment="Custom alert message")
    
    # Notification settings
    notify_email = Column(Boolean, nullable=False, default=False, comment="Send email notification")
    notify_push = Column(Boolean, nullable=False, default=True, comment="Send push notification")
    notify_webhook = Column(String(500), nullable=True, comment="Webhook URL")
    
    # Status
    status = Column(String(20), nullable=False, default="ACTIVE", comment="Alert status")
    trigger_count = Column(Integer, nullable=False, default=0, comment="Number of times triggered")
    last_triggered_at = Column(DateTime(timezone=True), nullable=True, comment="Last trigger timestamp")
    expires_at = Column(DateTime(timezone=True), nullable=True, comment="Auto-disable after this time")
    
    # Relationships
    user = relationship("UserModel", back_populates="alerts")
    symbol_ref = relationship("SymbolModel", foreign_keys=[symbol, exchange_id],
                              primaryjoin="and_(AlertModel.symbol==SymbolModel.symbol, AlertModel.exchange_id==SymbolModel.exchange_id)",
                              viewonly=True)


class EventQueueModel(Base):
    """Event queue for async processing (no soft delete, TTL cleanup)."""
    
    __tablename__ = "event_queue"
    __table_args__ = (
        Index('idx_event_queue_status_created', 'status', 'created_at'),
        Index('idx_event_queue_event_id', 'event_id', unique=True),
        Index('idx_event_queue_expires_at', 'expires_at'),
        CheckConstraint("status IN ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED')", name='ck_event_queue_status'),
        CheckConstraint("event_type IN ('ORDER_FILLED', 'POSITION_UPDATED', 'ALERT_TRIGGERED', 'BOT_ERROR', 'RISK_VIOLATION')", name='ck_event_queue_type'),
        {'comment': 'Event queue for async processing'}
    )
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="Auto-increment ID")
    event_id = Column(UUID(as_uuid=True), unique=True, nullable=False, comment="UUID v7 for deduplication")
    event_type = Column(String(50), nullable=False, comment="Event type")
    payload = Column(JSONType, nullable=False, comment="Event payload (JSON)")
    
    status = Column(String(20), nullable=False, default="PENDING", comment="Processing status")
    retry_count = Column(Integer, nullable=False, default=0, comment="Retry attempts")
    error_message = Column(String(500), nullable=True, comment="Error message if failed")
    
    created_at = Column(DateTime(timezone=True), nullable=False, comment="Event creation time")
    processed_at = Column(DateTime(timezone=True), nullable=True, comment="Processing completion time")
    expires_at = Column(DateTime(timezone=True), nullable=True, comment="TTL for cleanup")
