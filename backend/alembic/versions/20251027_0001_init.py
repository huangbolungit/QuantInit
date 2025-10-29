"""init strategies and signals tables

Revision ID: 20251027_0001
Revises: 
Create Date: 2025-10-27 00:00:00

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20251027_0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'strategies',
        sa.Column('id', sa.String(length=64), primary_key=True, index=True),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('strategy_type', sa.String(length=50), nullable=False),
        sa.Column('parameters', sa.JSON(), nullable=False),
        sa.Column('stock_pool', sa.JSON(), nullable=False),
        sa.Column('rebalance_frequency', sa.Integer(), nullable=False, server_default='10'),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='active'),
        sa.Column('performance_metrics', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_signal_time', sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        'strategy_signals',
        sa.Column('id', sa.String(length=64), primary_key=True, index=True),
        sa.Column('strategy_id', sa.String(length=64), sa.ForeignKey('strategies.id'), index=True, nullable=False),
        sa.Column('stock_code', sa.String(length=16), index=True, nullable=False),
        sa.Column('signal_type', sa.String(length=10), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('price', sa.Float(), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('expected_return', sa.Float(), nullable=True),
        sa.Column('risk_level', sa.String(length=20), nullable=True),
        sa.Column('parameters', sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('strategy_signals')
    op.drop_table('strategies')

