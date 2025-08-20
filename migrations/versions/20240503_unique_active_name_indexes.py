"""add unique index on name and user_id for active records"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20240503'
down_revision = '20240502'
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(
        'uq_account_user_name_active',
        'account',
        [sa.text('lower(name)'), 'user_id'],
        unique=True,
        sqlite_where=sa.text('deleted_at IS NULL'),
        postgresql_where=sa.text('deleted_at IS NULL'),
    )
    op.create_index(
        'uq_category_user_name_active',
        'category',
        [sa.text('lower(name)'), 'user_id'],
        unique=True,
        sqlite_where=sa.text('deleted_at IS NULL'),
        postgresql_where=sa.text('deleted_at IS NULL'),
    )


def downgrade():
    op.drop_index('uq_category_user_name_active', table_name='category')
    op.drop_index('uq_account_user_name_active', table_name='account')
