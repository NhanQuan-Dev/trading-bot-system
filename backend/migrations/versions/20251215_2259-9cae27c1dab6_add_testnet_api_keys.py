"""add_testnet_api_keys

Revision ID: 9cae27c1dab6
Revises: c6f60b28d88e
Create Date: 2025-12-15 22:59:39.373773

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9cae27c1dab6'
down_revision: Union[str, Sequence[str], None] = 'c6f60b28d88e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add testnet API key columns to api_connections table
    op.add_column('api_connections', sa.Column('testnet_api_key_encrypted', sa.Text(), nullable=True, comment='Encrypted testnet API key (Fernet)'))
    op.add_column('api_connections', sa.Column('testnet_secret_key_encrypted', sa.Text(), nullable=True, comment='Encrypted testnet secret key (Fernet)'))


def downgrade() -> None:
    """Downgrade schema."""
    # Drop testnet API key columns
    op.drop_column('api_connections', 'testnet_secret_key_encrypted')
    op.drop_column('api_connections', 'testnet_api_key_encrypted')
