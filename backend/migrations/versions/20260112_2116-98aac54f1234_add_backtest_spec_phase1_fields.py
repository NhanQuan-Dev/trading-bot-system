"""add backtest spec phase 1 fields

Revision ID: 98aac54f1234
Revises: d0bb1f80c697
Create Date: 2026-01-12 21:16:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '98aac54f1234'
down_revision = 'd0bb1f80c697'
branch_labels = None
depends_on = None


def upgrade():
    """Add spec-required fields to backtest_trades and backtest_runs tables."""
    
    # Add fields to backtest_trades
    op.add_column('backtest_trades', sa.Column('signal_time', sa.DateTime(timezone=True), nullable=True))
    op.add_column('backtest_trades', sa.Column('execution_delay_seconds', sa.Float(), nullable=True))
    op.add_column('backtest_trades', sa.Column('max_drawdown', sa.Numeric(precision=20, scale=8), nullable=True, server_default='0'))
    op.add_column('backtest_trades', sa.Column('max_runup', sa.Numeric(precision=20, scale=8), nullable=True, server_default='0'))
    op.add_column('backtest_trades', sa.Column('fill_policy_used', sa.String(length=20), nullable=True))
    op.add_column('backtest_trades', sa.Column('fill_conditions_met', sa.JSON(), nullable=True))
    
    # Add fields to backtest_runs (assuming config stored as JSON column)
    # If config is separate columns, add these:
    # op.add_column('backtest_runs', sa.Column('fill_policy', sa.String(length=20), nullable=True, server_default='optimistic'))
    # op.add_column('backtest_runs', sa.Column('price_path_assumption', sa.String(length=20), nullable=True, server_default='neutral'))


def downgrade():
    """Remove spec-required fields."""
    
    # Remove from backtest_trades
    op.drop_column('backtest_trades', 'fill_conditions_met')
    op.drop_column('backtest_trades', 'fill_policy_used')
    op.drop_column('backtest_trades', 'max_runup')
    op.drop_column('backtest_trades', 'max_drawdown')
    op.drop_column('backtest_trades', 'execution_delay_seconds')
    op.drop_column('backtest_trades', 'signal_time')
    
    # Remove from backtest_runs if added above
    # op.drop_column('backtest_runs', 'price_path_assumption')
    # op.drop_column('backtest_runs', 'fill_policy')
