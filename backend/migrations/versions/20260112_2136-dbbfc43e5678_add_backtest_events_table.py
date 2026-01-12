"""add backtest events table

Revision ID: dbbfc43e5678
Revises: 98aac54f1234
Create Date: 2026-01-12 21:36:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'dbbfc43e5678'
down_revision = '98aac54f1234'
branch_labels = None
depends_on = None


def upgrade():
    """Create backtest_events table for event architecture."""
    
    op.create_table(
        'backtest_events',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('backtest_id', sa.UUID(), nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['backtest_id'], ['backtest_runs.id'], ondelete='CASCADE'),
    )
    
    # Create index for efficient queries
    op.create_index('idx_backtest_events_backtest_id', 'backtest_events', ['backtest_id'])
    op.create_index('idx_backtest_events_event_type', 'backtest_events', ['event_type'])
    op.create_index('idx_backtest_events_timestamp', 'backtest_events', ['timestamp'])


def downgrade():
    """Remove backtest_events table."""
    
    op.drop_index('idx_backtest_events_timestamp', table_name='backtest_events')
    op.drop_index('idx_backtest_events_event_type', table_name='backtest_events')
    op.drop_index('idx_backtest_events_backtest_id', table_name='backtest_events')
    op.drop_table('backtest_events')
