"""Add exchange_connection_id to backtest_runs table.

Revision ID: 20251221_2223
Revises: 20251219_1200-8f3d1a2b3c4d
Create Date: 2025-12-21 22:23:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '8f3d1a2b3c4d'

branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



def upgrade() -> None:
    # First, delete all existing backtest data (as requested by user)
    # Delete in order to respect foreign key constraints
    op.execute("DELETE FROM backtest_trades")
    op.execute("DELETE FROM backtest_results")
    op.execute("DELETE FROM backtest_runs")
    
    # Add exchange_connection_id column to backtest_runs
    op.add_column(
        'backtest_runs',
        sa.Column(
            'exchange_connection_id',
            sa.UUID(),
            sa.ForeignKey('api_connections.id', ondelete='RESTRICT'),
            nullable=False,  # Required - user must select exchange
            comment='Exchange connection used for candle data'
        )
    )
    
    # Add index for performance
    op.create_index(
        'idx_backtest_runs_exchange_connection',
        'backtest_runs',
        ['exchange_connection_id']
    )


def downgrade() -> None:
    # Remove index
    op.drop_index('idx_backtest_runs_exchange_connection', table_name='backtest_runs')
    
    # Remove column
    op.drop_column('backtest_runs', 'exchange_connection_id')
