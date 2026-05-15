from typing import Optional

from pydantic import BaseModel, ConfigDict


class DeployPathConfigRead(BaseModel):
    """部署路径配置 — 读取响应"""

    deploy_type: str
    target_dir: str
    backup_dir: str
    parent_dir: str
    folder_name: str
    restart_commands: list[str]
    container_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class DeployPathConfigUpdate(BaseModel):
    """部署路径配置 — 更新请求"""

    target_dir: str
    backup_dir: str
    parent_dir: str
    folder_name: str
    restart_commands: list[str]
    container_name: Optional[str] = None
