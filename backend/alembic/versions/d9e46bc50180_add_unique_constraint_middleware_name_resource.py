"""add unique constraint for middleware name + resource_id

Revision ID: d9e46bc50180
Revises: c8f35ab49079
Create Date: 2026-02-24 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd9e46bc50180'
down_revision = 'c8f35ab49079'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 添加联合唯一约束：同一资源下中间件名称唯一
    op.create_unique_constraint(
        'uq_middleware_name_resource',
        'middlewares',
        ['name', 'resource_id']
    )


def downgrade() -> None:
    # 移除联合唯一约束
    op.drop_constraint('uq_middleware_name_resource', 'middlewares', type_='unique')
