"""add indexes for strategies and strategy_signals

Revision ID: 20251027_0002
Revises: 20251027_0001
Create Date: 2025-10-27 00:15:00

"""
from alembic import op
import sqlalchemy as sa

revision = '20251027_0002'
down_revision = '20251027_0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # strategy_signals indexes
    op.create_index('ix_strategy_signals_strategy_id', 'strategy_signals', ['strategy_id'], unique=False)
    op.create_index('ix_strategy_signals_timestamp', 'strategy_signals', ['timestamp'], unique=False)
    op.create_index('ix_strategy_signals_stock_code', 'strategy_signals', ['stock_code'], unique=False)
    # strategies indexes
    op.create_index('ix_strategies_status', 'strategies', ['status'], unique=False)
    op.create_index('ix_strategies_created_at', 'strategies', ['created_at'], unique=False)


def downgrade() -> None:
    # drop in reverse order
    op.drop_index('ix_strategies_created_at', table_name='strategies')
    op.drop_index('ix_strategies_status', table_name='strategies')
    op.drop_index('ix_strategy_signals_stock_code', table_name='strategy_signals')
    op.drop_index('ix_strategy_signals_timestamp', table_name='strategy_signals')
    op.drop_index('ix_strategy_signals_strategy_id', table_name='strategy_signals')

