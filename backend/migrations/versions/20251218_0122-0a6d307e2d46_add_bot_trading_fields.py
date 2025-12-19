"""add_bot_trading_fields

Revision ID: 0a6d307e2d46
Revises: 46cf8b4fcb0a
Create Date: 2025-12-18 01:22:09.976173

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0a6d307e2d46'
down_revision: Union[str, Sequence[str], None] = '46cf8b4fcb0a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
