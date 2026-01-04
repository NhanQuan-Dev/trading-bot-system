"""Add client_order_id to orders

Revision ID: d0bb1f80c697
Revises: 8f78ce97504d
Create Date: 2026-01-04 14:18:45.123456

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'd0bb1f80c697'
down_revision: Union[str, Sequence[str], None] = '8f78ce97504d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('orders', sa.Column('client_order_id', sa.String(length=100), nullable=True, comment='Client order ID'))
    op.create_unique_constraint(None, 'orders', ['client_order_id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(None, 'orders', type_='unique')
    op.drop_column('orders', 'client_order_id')
