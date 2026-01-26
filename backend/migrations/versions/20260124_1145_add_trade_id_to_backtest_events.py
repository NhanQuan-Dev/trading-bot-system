"""add trade_id to backtest_events

Revision ID: 20260124_add_trade_id
Revises: 45b52c5dfac0
Create Date: 2026-01-23 11:45:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260124_add_trade_id'
down_revision = '45b52c5dfac0'
branch_labels = None
depends_on = None


def upgrade():
    # Add trade_id column to backtest_events
    op.add_column('backtest_events', sa.Column('trade_id', sa.UUID(), nullable=True))
    op.create_foreign_key('fk_backtest_events_trade_id', 'backtest_events', 'backtest_trades', ['trade_id'], ['id'], ondelete='CASCADE')
    op.create_index('idx_backtest_events_trade_id', 'backtest_events', ['trade_id'])


def downgrade():
    op.drop_index('idx_backtest_events_trade_id', table_name='backtest_events')
    op.drop_constraint('fk_backtest_events_trade_id', 'backtest_events', type_='foreignkey')
    op.drop_column('backtest_events', 'trade_id')
