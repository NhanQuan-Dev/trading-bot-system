"""add_is_testnet_column

Revision ID: 8f3d1a2b3c4d
Revises: 6b4d20eeb5de
Create Date: 2025-12-19 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8f3d1a2b3c4d'
down_revision: Union[str, Sequence[str], None] = '6b4d20eeb5de'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add `is_testnet` boolean column to `api_connections`.

    New column defaults to false for existing rows.
    """
    # Use a server default to populate existing rows; then remove server_default.
    op.add_column(
        'api_connections',
        sa.Column('is_testnet', sa.Boolean(), nullable=False, server_default=sa.text('false')),
    )
    # Optional: create an index if needed in future. For now keep simple.
    # Remove server_default to let application control defaults going forward.
    with op.get_context().autocommit_block():
        op.alter_column('api_connections', 'is_testnet', server_default=None)


def downgrade() -> None:
    """Remove `is_testnet` column from `api_connections`."""
    op.drop_column('api_connections', 'is_testnet')
