"""Add bot_id user_id to trades

Revision ID: 8f78ce97504d
Revises: add_bot_stats_fields_20251225
Create Date: 2026-01-04 14:08:38.942772

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '8f78ce97504d'
down_revision: Union[str, Sequence[str], None] = 'add_bot_stats_fields_20251225'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('trades', sa.Column('user_id', sa.UUID(), nullable=False))
    op.add_column('trades', sa.Column('bot_id', sa.UUID(), nullable=True, comment='Bot executed this trade'))
    op.create_foreign_key(None, 'trades', 'users', ['user_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key(None, 'trades', 'bots', ['bot_id'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(None, 'trades', type_='foreignkey')
    op.drop_constraint(None, 'trades', type_='foreignkey')
    op.drop_column('trades', 'bot_id')
    op.drop_column('trades', 'user_id')
