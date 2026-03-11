"""add deploy operation types

Revision ID: e3f4a5b6c7d8
Revises: d9e46bc50180
Create Date: 2026-03-11 12:00:00.000000
"""

from alembic import op


revision = 'e3f4a5b6c7d8'
down_revision = 'd9e46bc50180'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE operationtype ADD VALUE IF NOT EXISTS 'backend_deploy';")
    op.execute("ALTER TYPE operationtype ADD VALUE IF NOT EXISTS 'algorithm_deploy';")


def downgrade() -> None:
    pass
