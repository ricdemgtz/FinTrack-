"""add scope_account_id to rule

Revision ID: 20240502
Revises: 20240501
Create Date: 2024-05-02 00:00:00
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20240502'
down_revision = '20240501'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('rule', sa.Column('scope_account_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'rule', 'account', ['scope_account_id'], ['id'])


def downgrade():
    op.drop_constraint(None, 'rule', type_='foreignkey')
    op.drop_column('rule', 'scope_account_id')
