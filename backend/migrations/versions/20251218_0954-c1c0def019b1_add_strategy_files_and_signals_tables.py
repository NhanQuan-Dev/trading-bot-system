"""add_strategy_files_and_signals_tables

Revision ID: c1c0def019b1
Revises: b45d2a8fdea4
Create Date: 2025-12-18 09:54:36.320173

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c1c0def019b1'
down_revision: Union[str, Sequence[str], None] = 'b45d2a8fdea4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create strategy_files table (catalog of strategy plugins)
    op.create_table(
        'strategy_files',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('strategy_type', sa.String(length=20), nullable=False, comment='Unique strategy type identifier'),
        sa.Column('file_path', sa.String(length=500), nullable=False, comment='Relative path to strategy Python file'),
        sa.Column('module_name', sa.String(length=200), nullable=False, comment='Python module name for importing'),
        sa.Column('class_name', sa.String(length=100), nullable=False, comment='Strategy class name'),
        sa.Column('display_name', sa.String(length=100), nullable=False, comment='Human-readable strategy name'),
        sa.Column('description', sa.Text(), nullable=True, comment='Strategy description'),
        sa.Column('author', sa.String(length=100), nullable=True, comment='Strategy author'),
        sa.Column('version', sa.String(length=20), nullable=False, server_default='1.0.0', comment='Strategy version'),
        sa.Column('parameters_schema', sa.JSON().with_variant(sa.dialects.postgresql.JSONB(), 'postgresql'), nullable=False, comment='JSON Schema for strategy parameters'),
        sa.Column('compatibility', sa.JSON().with_variant(sa.dialects.postgresql.JSONB(), 'postgresql'), nullable=False, server_default='{}', comment='Strategy compatibility constraints'),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default='true', comment='Whether strategy is enabled for use'),
        sa.Column('is_builtin', sa.Boolean(), nullable=False, server_default='true', comment='Whether strategy is a builtin system strategy'),
        sa.Column('last_validated_at', sa.TIMESTAMP(timezone=True), nullable=True, comment='Last validation timestamp'),
        sa.Column('validation_errors', sa.JSON().with_variant(sa.dialects.postgresql.JSONB(), 'postgresql'), nullable=True, comment='Validation errors if any'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('strategy_type'),
        comment='Strategy file catalog (global registry of strategy plugins)'
    )
    op.create_index('ix_strategy_files_strategy_type', 'strategy_files', ['strategy_type'])
    op.create_index('ix_strategy_files_is_enabled', 'strategy_files', ['is_enabled'])

    # Create strategy_signals table (audit trail)
    op.create_table(
        'strategy_signals',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('bot_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False, comment='Bot that generated the signal'),
        sa.Column('strategy_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False, comment='Strategy instance that generated the signal'),
        sa.Column('signal_type', sa.String(length=10), nullable=False, comment='Signal type (BUY, SELL, CLOSE, HOLD)'),
        sa.Column('symbol', sa.String(length=20), nullable=False, comment='Trading symbol'),
        sa.Column('price', sa.String(length=50), nullable=True, comment='Signal price (stored as string to preserve precision)'),
        sa.Column('quantity', sa.String(length=50), nullable=True, comment='Signal quantity (stored as string to preserve precision)'),
        sa.Column('confidence', sa.String(length=20), nullable=True, comment='Signal confidence (0.0 - 1.0)'),
        sa.Column('reason', sa.Text(), nullable=True, comment='Reason for signal'),
        sa.Column('signal_metadata', sa.JSON().with_variant(sa.dialects.postgresql.JSONB(), 'postgresql'), nullable=False, server_default='{}', comment='Additional signal metadata'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id'),
        comment='Strategy signals audit trail'
    )
    op.create_index('ix_strategy_signals_bot_id', 'strategy_signals', ['bot_id'])
    op.create_index('ix_strategy_signals_strategy_id', 'strategy_signals', ['strategy_id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_strategy_signals_strategy_id', table_name='strategy_signals')
    op.drop_index('ix_strategy_signals_bot_id', table_name='strategy_signals')
    op.drop_table('strategy_signals')
    
    op.drop_index('ix_strategy_files_is_enabled', table_name='strategy_files')
    op.drop_index('ix_strategy_files_strategy_type', table_name='strategy_files')
    op.drop_table('strategy_files')
