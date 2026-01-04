"""Add status_message column to backtest_runs.

Revision ID: add_status_message_backtest
Revises: d31c323aa982
Create Date: 2025-12-23
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_status_message_backtest'
down_revision = 'd31c323aa982'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add status_message column to backtest_runs
    op.add_column('backtest_runs', sa.Column(
        'status_message', 
        sa.String(200), 
        nullable=True,
        comment='User-friendly progress message'
    ))


def downgrade() -> None:
    op.drop_column('backtest_runs', 'status_message')
