"""make rule_id nullable

Revision ID: 2b3c4d5e6f7g
Revises: 1a2b3c4d5e6f
Create Date: 2026-02-04 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2b3c4d5e6f7g'
down_revision = '1a2b3c4d5e6f'  # This should be the ID of the middleware migration
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('alerts', 'rule_id', existing_type=sa.Integer(), nullable=True)


def downgrade():
    op.alter_column('alerts', 'rule_id', existing_type=sa.Integer(), nullable=False)
