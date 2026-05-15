from sqlalchemy import Column, DateTime, Integer, String, JSON
from sqlalchemy.sql import func

from app.core.database import Base


class DeployPathConfig(Base):
    """部署路径配置表 — 存储各部署类型的远程路径、备份路径和重启命令"""

    __tablename__ = "deploy_path_configs"

    id = Column(Integer, primary_key=True, index=True)
    deploy_type = Column(String(20), unique=True, nullable=False, index=True)
    target_dir = Column(String(255), nullable=False)
    backup_dir = Column(String(255), nullable=False)
    parent_dir = Column(String(255), nullable=False)
    folder_name = Column(String(100), nullable=False)
    restart_commands = Column(JSON, nullable=False, default=list)
    container_name = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return (
            f"<DeployPathConfig(deploy_type='{self.deploy_type}', "
            f"target_dir='{self.target_dir}')>"
        )
