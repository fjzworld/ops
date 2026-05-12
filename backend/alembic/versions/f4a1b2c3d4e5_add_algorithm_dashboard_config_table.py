"""add algorithm dashboard config table

Revision ID: f4a1b2c3d4e5
Revises: e3f4a5b6c7d8
Create Date: 2026-05-08 10:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "f4a1b2c3d4e5"
down_revision = "e3f4a5b6c7d8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "algorithm_dashboard_configs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("host", sa.String(length=255), nullable=False),
        sa.Column("port", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=120), nullable=False),
        sa.Column("password_enc", sa.String(), nullable=True),
        sa.Column("database_name", sa.String(length=120), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_algorithm_dashboard_configs_id"),
        "algorithm_dashboard_configs",
        ["id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_algorithm_dashboard_configs_id"),
        table_name="algorithm_dashboard_configs",
    )
    op.drop_table("algorithm_dashboard_configs")
