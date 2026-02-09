"""
Docker Container Management API
Provides endpoints to list, start, stop, restart containers and view logs
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from app.core.database import get_db
from app.core.encryption import decrypt_string
from app.models.user import User
from app.models.resource import Resource
from app.api.v1.auth import get_current_active_user
from app.services.resource_detector import SSHCredentials
from app.services.docker_service import DockerService, Container

logger = logging.getLogger(__name__)
router = APIRouter()


class ContainerResponse(BaseModel):
    """Container list response"""
    resource_id: int
    resource_name: str
    containers: List[Container]


class ContainerLogsResponse(BaseModel):
    """Container logs response"""
    container_id: str
    logs: str


class MessageResponse(BaseModel):
    """Simple message response"""
    message: str
    success: bool = True


def get_ssh_credentials(resource: Resource) -> SSHCredentials:
    """
    Build SSH credentials from resource record.
    Raises HTTPException if credentials are not available.
    """
    if not resource.ip_address:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="资源没有配置 IP 地址"
        )
    
    password = None
    private_key = None
    decryption_failed = False
    
    if resource.ssh_password_enc:
        password = decrypt_string(resource.ssh_password_enc)
        if password is None:
            decryption_failed = True
    if resource.ssh_private_key_enc:
        private_key = decrypt_string(resource.ssh_private_key_enc)
        if private_key is None:
            decryption_failed = True
    
    if not password and not private_key:
        if decryption_failed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="SSH 凭据解密失败，请重新添加资源以更新凭据"
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="资源没有保存 SSH 凭据，无法连接"
        )
    
    return SSHCredentials(
        host=resource.ip_address,
        port=resource.ssh_port or 22,
        username=resource.ssh_username or "root",
        password=password,
        private_key=private_key
    )


@router.get("/{resource_id}/containers", response_model=ContainerResponse)
async def list_containers(
    resource_id: int,
    all: bool = Query(True, description="Include stopped containers"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List all Docker containers on a resource"""
    resource = db.query(Resource).filter(Resource.id == resource_id).first()
    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="资源不存在"
        )
    
    try:
        credentials = get_ssh_credentials(resource)
        docker_service = DockerService(credentials)
        containers = docker_service.list_containers(all_containers=all)
        
        return ContainerResponse(
            resource_id=resource_id,
            resource_name=resource.name,
            containers=containers
        )
    except HTTPException:
        # Re-raise HTTPException as-is (e.g., missing credentials, no IP)
        raise
    except Exception as e:
        # Log full traceback for debugging
        logger.exception(f"Failed to list containers for resource {resource_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"连接服务器失败: {str(e)}"
        )


@router.post("/{resource_id}/containers/{container_id}/start", response_model=MessageResponse)
async def start_container(
    resource_id: int,
    container_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Start a stopped container"""
    resource = db.query(Resource).filter(Resource.id == resource_id).first()
    if not resource:
        raise HTTPException(status_code=404, detail="资源不存在")
    
    try:
        credentials = get_ssh_credentials(resource)
        docker_service = DockerService(credentials)
        docker_service.start_container(container_id)
        return MessageResponse(message=f"容器 {container_id} 已启动")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{resource_id}/containers/{container_id}/stop", response_model=MessageResponse)
async def stop_container(
    resource_id: int,
    container_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Stop a running container"""
    resource = db.query(Resource).filter(Resource.id == resource_id).first()
    if not resource:
        raise HTTPException(status_code=404, detail="资源不存在")
    
    try:
        credentials = get_ssh_credentials(resource)
        docker_service = DockerService(credentials)
        docker_service.stop_container(container_id)
        return MessageResponse(message=f"容器 {container_id} 已停止")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{resource_id}/containers/{container_id}/restart", response_model=MessageResponse)
async def restart_container(
    resource_id: int,
    container_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Restart a container"""
    resource = db.query(Resource).filter(Resource.id == resource_id).first()
    if not resource:
        raise HTTPException(status_code=404, detail="资源不存在")
    
    try:
        credentials = get_ssh_credentials(resource)
        docker_service = DockerService(credentials)
        docker_service.restart_container(container_id)
        return MessageResponse(message=f"容器 {container_id} 已重启")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{resource_id}/containers/{container_id}/logs", response_model=ContainerLogsResponse)
async def get_container_logs(
    resource_id: int,
    container_id: str,
    tail: int = Query(100, ge=10, le=1000, description="Number of lines"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get container logs"""
    resource = db.query(Resource).filter(Resource.id == resource_id).first()
    if not resource:
        raise HTTPException(status_code=404, detail="资源不存在")
    
    try:
        credentials = get_ssh_credentials(resource)
        docker_service = DockerService(credentials)
        logs = docker_service.get_logs(container_id, tail=tail)
        return ContainerLogsResponse(container_id=container_id, logs=logs)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
