"""add_bot_stats_fields

Revision ID: add_bot_stats_fields_20251225
Revises: add_status_message_backtest
Create Date: 2025-12-25 09:15:00.000000

"""
from alembic import op
import sqlalchemy as sa
from decimal import Decimal


# revision identifiers, used by Alembic.
revision = 'add_bot_stats_fields_20251225'
down_revision = 'add_status_message_backtest'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add cumulative bot stats fields
    op.add_column('bots', sa.Column('total_pnl', sa.DECIMAL(20, 8), nullable=False, server_default='0', comment='Total realized P&L from all closed trades'))
    op.add_column('bots', sa.Column('total_trades', sa.Integer(), nullable=False, server_default='0', comment='Total number of closed trades'))
    op.add_column('bots', sa.Column('winning_trades', sa.Integer(), nullable=False, server_default='0', comment='Number of winning trades (P&L > 0)'))
    op.add_column('bots', sa.Column('losing_trades', sa.Integer(), nullable=False, server_default='0', comment='Number of losing trades (P&L < 0)'))
    
    # Add streak tracking fields
    op.add_column('bots', sa.Column('current_win_streak', sa.Integer(), nullable=False, server_default='0', comment='Current consecutive winning trades'))
    op.add_column('bots', sa.Column('current_loss_streak', sa.Integer(), nullable=False, server_default='0', comment='Current consecutive losing trades'))
    op.add_column('bots', sa.Column('max_win_streak', sa.Integer(), nullable=False, server_default='0', comment='Maximum win streak ever achieved'))
    op.add_column('bots', sa.Column('max_loss_streak', sa.Integer(), nullable=False, server_default='0', comment='Maximum loss streak ever experienced'))
    
    # Add index for total_pnl (for sorting by P&L)
    op.create_index('idx_bots_total_pnl', 'bots', ['total_pnl'], unique=False)


def downgrade() -> None:
    # Remove index
    op.drop_index('idx_bots_total_pnl', table_name='bots')
    
    # Remove streak tracking fields
    op.drop_column('bots', 'max_loss_streak')
    op.drop_column('bots', 'max_win_streak')
    op.drop_column('bots', 'current_loss_streak')
    op.drop_column('bots', 'current_win_streak')
    
    # Remove cumulative bot stats fields
    op.drop_column('bots', 'losing_trades')
    op.drop_column('bots', 'winning_trades')
    op.drop_column('bots', 'total_trades')
    op.drop_column('bots', 'total_pnl')
