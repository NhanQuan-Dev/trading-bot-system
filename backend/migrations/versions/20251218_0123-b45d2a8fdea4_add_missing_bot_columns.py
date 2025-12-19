"""add_missing_bot_columns

Revision ID: b45d2a8fdea4
Revises: 0a6d307e2d46
Create Date: 2025-12-18 01:23:52.729600

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b45d2a8fdea4'
down_revision: Union[str, Sequence[str], None] = '0a6d307e2d46'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add missing columns to bots table
    op.add_column('bots', sa.Column('exchange_connection_id', sa.UUID(), nullable=True))
    op.add_column('bots', sa.Column('description', sa.String(500), nullable=True))
    op.add_column('bots', sa.Column('risk_level', sa.String(20), nullable=False, server_default='MODERATE'))
    op.add_column('bots', sa.Column('configuration', sa.JSON(), nullable=False, server_default='{}'))
    op.add_column('bots', sa.Column('start_time', sa.TIMESTAMP(), nullable=True))
    op.add_column('bots', sa.Column('stop_time', sa.TIMESTAMP(), nullable=True))
    op.add_column('bots', sa.Column('last_error', sa.String(1000), nullable=True))
    op.add_column('bots', sa.Column('performance', sa.JSON(), nullable=False, server_default='{}'))
    op.add_column('bots', sa.Column('active_orders', sa.JSON(), nullable=False, server_default='[]'))
    op.add_column('bots', sa.Column('daily_pnl', sa.DECIMAL(precision=20, scale=8), nullable=True))
    op.add_column('bots', sa.Column('total_runtime_seconds', sa.Integer(), nullable=True, server_default='0'))
    op.add_column('bots', sa.Column('meta_data', sa.JSON(), nullable=True))
    
    # Add foreign key constraint
    op.create_foreign_key(
        'fk_bots_exchange_connection_id',
        'bots', 'api_connections',
        ['exchange_connection_id'], ['id'],
        ondelete='RESTRICT'
    )
    
    # Add indexes
    op.create_index('idx_bots_api_connection_id', 'bots', ['exchange_connection_id'])
    op.create_index('idx_bots_start_time', 'bots', ['start_time'])
    
    # Add check constraints
    op.create_check_constraint(
        'ck_bots_status',
        'bots',
        "status IN ('ACTIVE', 'PAUSED', 'STOPPED', 'ERROR', 'STARTING', 'STOPPING')"
    )
    op.create_check_constraint(
        'ck_bots_risk_level',
        'bots',
        "risk_level IN ('CONSERVATIVE', 'MODERATE', 'AGGRESSIVE', 'EXTREME')"
    )
    
    # Rename 'config' to match if it exists, or drop old columns
    # Since we're adding 'configuration', we should handle the old 'config' column
    op.execute("UPDATE bots SET configuration = COALESCE(config, '{}'::json) WHERE config IS NOT NULL")
    op.execute("UPDATE bots SET performance = COALESCE(performance_stats, '{}'::json) WHERE performance_stats IS NOT NULL")
    
    # Drop old columns that are replaced
    op.drop_column('bots', 'config')
    op.drop_column('bots', 'performance_stats')
    op.drop_column('bots', 'last_run_at')
    op.drop_column('bots', 'error_message')


def downgrade() -> None:
    """Downgrade schema."""
    # Restore old columns
    op.add_column('bots', sa.Column('config', sa.JSON(), nullable=True))
    op.add_column('bots', sa.Column('performance_stats', sa.JSON(), nullable=True))
    op.add_column('bots', sa.Column('last_run_at', sa.TIMESTAMP(), nullable=True))
    op.add_column('bots', sa.Column('error_message', sa.String(500), nullable=True))
    
    # Copy data back
    op.execute("UPDATE bots SET config = configuration")
    op.execute("UPDATE bots SET performance_stats = performance")
    op.execute("UPDATE bots SET error_message = last_error")
    
    # Drop constraints and indexes
    op.drop_constraint('ck_bots_risk_level', 'bots', type_='check')
    op.drop_constraint('ck_bots_status', 'bots', type_='check')
    op.drop_index('idx_bots_start_time', 'bots')
    op.drop_index('idx_bots_api_connection_id', 'bots')
    op.drop_constraint('fk_bots_exchange_connection_id', 'bots', type_='foreignkey')
    
    # Drop new columns
    op.drop_column('bots', 'meta_data')
    op.drop_column('bots', 'total_runtime_seconds')
    op.drop_column('bots', 'daily_pnl')
    op.drop_column('bots', 'active_orders')
    op.drop_column('bots', 'performance')
    op.drop_column('bots', 'last_error')
    op.drop_column('bots', 'stop_time')
    op.drop_column('bots', 'start_time')
    op.drop_column('bots', 'configuration')
    op.drop_column('bots', 'risk_level')
    op.drop_column('bots', 'description')
    op.drop_column('bots', 'exchange_connection_id')
