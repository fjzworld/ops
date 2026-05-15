import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import SessionLocal
from app.core.exceptions import BadRequestException, NotFoundException
from app.models.deploy_path_config import DeployPathConfig
from app.schemas.deploy_path import DeployPathConfigRead, DeployPathConfigUpdate

logger = logging.getLogger(__name__)

VALID_DEPLOY_TYPES = {"frontend", "backend", "algorithm"}


class DeployPathConfigService:
    @staticmethod
    async def get_all(db: AsyncSession) -> list[DeployPathConfigRead]:
        """获取所有部署类型的路径配置"""
        result = await db.execute(
            select(DeployPathConfig).order_by(DeployPathConfig.deploy_type.asc())
        )
        configs = result.scalars().all()
        return [DeployPathConfigRead.model_validate(c) for c in configs]

    @staticmethod
    async def upsert(
        db: AsyncSession,
        deploy_type: str,
        payload: DeployPathConfigUpdate,
    ) -> DeployPathConfigRead:
        """更新指定部署类型的路径配置"""
        if deploy_type not in VALID_DEPLOY_TYPES:
            raise BadRequestException(
                message=f"无效的部署类型: {deploy_type}"
            )

        result = await db.execute(
            select(DeployPathConfig).filter(
                DeployPathConfig.deploy_type == deploy_type
            )
        )
        config = result.scalars().first()
        if not config:
            raise NotFoundException(
                message=f"部署类型 {deploy_type} 的配置不存在"
            )

        config.target_dir = payload.target_dir.strip()
        config.backup_dir = payload.backup_dir.strip()
        config.parent_dir = payload.parent_dir.strip()
        config.folder_name = payload.folder_name.strip()
        config.restart_commands = payload.restart_commands
        config.container_name = payload.container_name

        await db.commit()
        await db.refresh(config)
        return DeployPathConfigRead.model_validate(config)

    @staticmethod
    def get_config(deploy_type: str) -> Optional[DeployPathConfig]:
        """同步获取指定部署类型的路径配置（供 deploy_service 使用）"""
        session = SessionLocal()
        try:
            result = session.execute(
                select(DeployPathConfig).filter(
                    DeployPathConfig.deploy_type == deploy_type
                )
            )
            return result.scalars().first()
        finally:
            session.close()
