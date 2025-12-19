"""add_risk_management_tables

Revision ID: 46cf8b4fcb0a
Revises: f3595aea39b7
Create Date: 2025-12-16 10:46:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '46cf8b4fcb0a'
down_revision = 'f3595aea39b7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create risk management tables."""
    # Create risk_limits table
    op.create_table('risk_limits',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('limit_type', sa.String(length=50), nullable=False),
        sa.Column('limit_value', sa.DECIMAL(precision=20, scale=8), nullable=False),
        sa.Column('symbol', sa.String(length=20), nullable=True),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('warning_threshold', sa.DECIMAL(precision=5, scale=2), nullable=False, server_default=sa.text('80.0')),
        sa.Column('critical_threshold', sa.DECIMAL(precision=5, scale=2), nullable=False, server_default=sa.text('95.0')),
        sa.Column('violations_data', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'")),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_risk_limits_user_id', 'risk_limits', ['user_id'], unique=False)
    op.create_index('ix_risk_limits_limit_type', 'risk_limits', ['limit_type'], unique=False)
    op.create_index('ix_risk_limits_symbol', 'risk_limits', ['symbol'], unique=False)
    op.create_index('ix_risk_limits_enabled', 'risk_limits', ['enabled'], unique=False)

    # Create risk_alerts table
    op.create_table('risk_alerts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('risk_limit_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('alert_type', sa.String(length=100), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('symbol', sa.String(length=20), nullable=True),
        sa.Column('current_value', sa.DECIMAL(precision=20, scale=8), nullable=False),
        sa.Column('limit_value', sa.DECIMAL(precision=20, scale=8), nullable=False),
        sa.Column('violation_percentage', sa.DECIMAL(precision=6, scale=2), nullable=False),
        sa.Column('acknowledged', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['risk_limit_id'], ['risk_limits.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_risk_alerts_user_id', 'risk_alerts', ['user_id'], unique=False)
    op.create_index('ix_risk_alerts_risk_limit_id', 'risk_alerts', ['risk_limit_id'], unique=False)
    op.create_index('ix_risk_alerts_alert_type', 'risk_alerts', ['alert_type'], unique=False)
    op.create_index('ix_risk_alerts_severity', 'risk_alerts', ['severity'], unique=False)
    op.create_index('ix_risk_alerts_symbol', 'risk_alerts', ['symbol'], unique=False)
    op.create_index('ix_risk_alerts_acknowledged', 'risk_alerts', ['acknowledged'], unique=False)
    op.create_index('ix_risk_alerts_created_at', 'risk_alerts', ['created_at'], unique=False)


def downgrade() -> None:
    """Drop risk management tables."""
    op.drop_index('ix_risk_alerts_created_at', table_name='risk_alerts')
    op.drop_index('ix_risk_alerts_acknowledged', table_name='risk_alerts')
    op.drop_index('ix_risk_alerts_symbol', table_name='risk_alerts')
    op.drop_index('ix_risk_alerts_severity', table_name='risk_alerts')
    op.drop_index('ix_risk_alerts_alert_type', table_name='risk_alerts')
    op.drop_index('ix_risk_alerts_risk_limit_id', table_name='risk_alerts')
    op.drop_index('ix_risk_alerts_user_id', table_name='risk_alerts')
    op.drop_table('risk_alerts')
    
    op.drop_index('ix_risk_limits_enabled', table_name='risk_limits')
    op.drop_index('ix_risk_limits_symbol', table_name='risk_limits')
    op.drop_index('ix_risk_limits_limit_type', table_name='risk_limits')
    op.drop_index('ix_risk_limits_user_id', table_name='risk_limits')
    op.drop_table('risk_limits')