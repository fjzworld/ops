"""add deploy path configs table

Revision ID: g5b6c7d8e9f0
Revises: f4a1b2c3d4e5
Create Date: 2026-05-14 14:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "g5b6c7d8e9f0"
down_revision = "f4a1b2c3d4e5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "deploy_path_configs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("deploy_type", sa.String(length=20), nullable=False),
        sa.Column("target_dir", sa.String(length=255), nullable=False),
        sa.Column("backup_dir", sa.String(length=255), nullable=False),
        sa.Column("parent_dir", sa.String(length=255), nullable=False),
        sa.Column("folder_name", sa.String(length=100), nullable=False),
        sa.Column("restart_commands", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("container_name", sa.String(length=100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("deploy_type"),
    )
    op.create_index(
        op.f("ix_deploy_path_configs_id"),
        "deploy_path_configs",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_deploy_path_configs_deploy_type"),
        "deploy_path_configs",
        ["deploy_type"],
        unique=True,
    )

    # 插入 3 条默认配置
    op.execute(
        sa.text(
            """
            INSERT INTO deploy_path_configs (deploy_type, target_dir, backup_dir, parent_dir, folder_name, restart_commands, container_name)
            VALUES
            ('frontend', '/usr/local/nginx/html', '/usr/local/nginx/backup', '/usr/local/nginx', 'html', '["docker restart start_nginx"]', 'start_nginx'),
            ('backend', '/data/rayshon_web', '/data/backup/rayshon_web', '/data', 'rayshon_web', '["docker-compose -f /data/rayshon_web/docker-compose.yml restart"]', NULL),
            ('algorithm', '/data/rayshon/python_server', '/data/backup/rayshon', '/data/rayshon', 'python_server', '["find /opt/start_container -name ''docker-compose.yml'' | sort | while read f; do (cd \\"$(dirname \\"$f\\")\\" && docker-compose restart); done"]', NULL)
            """
        )
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_deploy_path_configs_deploy_type"),
        table_name="deploy_path_configs",
    )
    op.drop_index(
        op.f("ix_deploy_path_configs_id"),
        table_name="deploy_path_configs",
    )
    op.drop_table("deploy_path_configs")
