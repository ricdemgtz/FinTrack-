"""add icon_emoji parent_id and is_system to category

Revision ID: 20240504
Revises: 20240503
Create Date: 2024-05-04 00:00:00
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20240504'
down_revision = '20240503'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('category', sa.Column('icon_emoji', sa.String(length=16), nullable=True))
    op.add_column('category', sa.Column('parent_id', sa.Integer(), nullable=True))
    op.add_column('category', sa.Column('is_system', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_foreign_key(None, 'category', 'category', ['parent_id'], ['id'])


def downgrade():
    op.drop_constraint(None, 'category', type_='foreignkey')
    op.drop_column('category', 'is_system')
    op.drop_column('category', 'parent_id')
    op.drop_column('category', 'icon_emoji')
