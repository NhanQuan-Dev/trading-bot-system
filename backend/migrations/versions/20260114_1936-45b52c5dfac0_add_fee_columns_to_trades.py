"""add_fee_columns_to_trades

Revision ID: 45b52c5dfac0
Revises: dbbfc43e5678
Create Date: 2026-01-14 19:36:07.484593

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '45b52c5dfac0'
down_revision: Union[str, Sequence[str], None] = 'dbbfc43e5678'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('backtest_trades', sa.Column('maker_fee', sa.DECIMAL(precision=20, scale=8), server_default='0', nullable=False))
    op.add_column('backtest_trades', sa.Column('taker_fee', sa.DECIMAL(precision=20, scale=8), server_default='0', nullable=False))
    op.add_column('backtest_trades', sa.Column('funding_fee', sa.DECIMAL(precision=20, scale=8), server_default='0', nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('backtest_trades', 'maker_fee')
    op.drop_column('backtest_trades', 'taker_fee')
    op.drop_column('backtest_trades', 'funding_fee')
