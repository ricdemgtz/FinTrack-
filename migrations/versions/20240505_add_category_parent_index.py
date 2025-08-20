"""add index to category.parent_id

Revision ID: 20240505
Revises: 20240504
Create Date: 2024-05-05 00:00:00
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20240505'
down_revision = '20240504'
branch_labels = None
depends_on = None

def upgrade():
    op.create_index('ix_category_parent_id', 'category', ['parent_id'])

def downgrade():
    op.drop_index('ix_category_parent_id', table_name='category')
