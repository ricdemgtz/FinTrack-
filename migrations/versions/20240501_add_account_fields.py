"""add opening_balance and active to account

Revision ID: 20240501
Revises: 
Create Date: 2024-05-01 00:00:00
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20240501'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('account', sa.Column('opening_balance', sa.Numeric(12, 2), nullable=False, server_default='0'))
    op.add_column('account', sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.true()))
    op.create_check_constraint('ck_account_opening_balance_non_negative', 'account', 'opening_balance >= 0')
    op.create_index('ix_account_active', 'account', ['active'])


def downgrade():
    op.drop_index('ix_account_active', table_name='account')
    op.drop_constraint('ck_account_opening_balance_non_negative', 'account', type_='check')
    op.drop_column('account', 'active')
    op.drop_column('account', 'opening_balance')
