"""rename_strategies_type_to_strategy_type

Revision ID: 6b4d20eeb5de
Revises: c1c0def019b1
Create Date: 2025-12-18 10:05:15.379356

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6b4d20eeb5de'
down_revision: Union[str, Sequence[str], None] = 'c1c0def019b1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Rename 'type' column to 'strategy_type'
    op.alter_column('strategies', 'type', new_column_name='strategy_type', existing_type=sa.String(20))
    
    # Add missing columns if they don't exist
    # We need to use try-except in case columns already exist
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [col['name'] for col in inspector.get_columns('strategies')]
    
    if 'is_active' not in columns:
        op.add_column('strategies', sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'))
    
    if 'backtest_results' not in columns:
        op.add_column('strategies', sa.Column('backtest_results', sa.JSON(), nullable=True))
    
    if 'live_performance' not in columns:
        op.add_column('strategies', sa.Column('live_performance', sa.JSON(), nullable=False, server_default='{}'))


def downgrade() -> None:
    """Downgrade schema."""
    # Rename back
    op.alter_column('strategies', 'strategy_type', new_column_name='type', existing_type=sa.String(20))
    
    # Remove added columns
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [col['name'] for col in inspector.get_columns('strategies')]
    
    if 'is_active' in columns:
        op.drop_column('strategies', 'is_active')
    
    if 'backtest_results' in columns:
        op.drop_column('strategies', 'backtest_results')
    
    if 'live_performance' in columns:
        op.drop_column('strategies', 'live_performance')
