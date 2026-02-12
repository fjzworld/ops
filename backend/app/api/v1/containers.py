"""
Docker Container Management API
Provides endpoints to list, start, stop, restart containers and view logs
"""
import logging
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from pydantic import BaseModel

from app.core.database import get_async_db
from app.core.encryption import encrypt_string
from app.models.user import User
from app.models.resource import Resource
from app.api.v1.auth import get_current_active_user
from app.services.credential_service import CredentialService
from app.services.resource_detector import SSHCredentials
from app.services.docker_service import DockerService, Container
from app.core.exceptions import AppException, NotFoundException, BadRequestException, InternalServerError


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


@router.get("/{resource_id}/containers", response_model=ContainerResponse)

async def list_containers(
    resource_id: int,
    all: bool = Query(True, description="Include stopped containers"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db)
):
    """List all Docker containers on a resource"""
    resource = await db.get(Resource, resource_id)
    if not resource:
        raise NotFoundException(message="资源不存在")
    
    try:
        credentials = CredentialService.get_ssh_credentials(resource)
        docker_service = DockerService(credentials)
        containers = docker_service.list_containers(all_containers=all)
        
        return ContainerResponse(
            resource_id=resource_id,
            resource_name=str(resource.name),
            containers=containers
        )
    except AppException:
        # Re-raise AppException as-is (e.g., missing credentials, no IP)
        raise
    except Exception as e:
        # Log full traceback for debugging
        logger.exception(f"Failed to list containers for resource {resource_id}")
        raise InternalServerError(message=f"连接服务器失败: {str(e)}")


@router.post("/{resource_id}/containers/{container_id}/start", response_model=MessageResponse)
async def start_container(
    resource_id: int,
    container_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Start a stopped container"""
    resource = await db.get(Resource, resource_id)
    if not resource:
        raise NotFoundException(message="资源不存在")
    
    try:
        credentials = CredentialService.get_ssh_credentials(resource)
        docker_service = DockerService(credentials)
        docker_service.start_container(container_id)
        return MessageResponse(message=f"容器 {container_id} 已启动")
    except Exception as e:
        raise InternalServerError(message=str(e))


@router.post("/{resource_id}/containers/{container_id}/stop", response_model=MessageResponse)
async def stop_container(
    resource_id: int,
    container_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Stop a running container"""
    resource = await db.get(Resource, resource_id)
    if not resource:
        raise NotFoundException(message="资源不存在")
    
    try:
        credentials = CredentialService.get_ssh_credentials(resource)
        docker_service = DockerService(credentials)
        docker_service.stop_container(container_id)
        return MessageResponse(message=f"容器 {container_id} 已停止")
    except Exception as e:
        raise InternalServerError(message=str(e))


@router.post("/{resource_id}/containers/{container_id}/restart", response_model=MessageResponse)
async def restart_container(
    resource_id: int,
    container_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Restart a container"""
    resource = await db.get(Resource, resource_id)
    if not resource:
        raise NotFoundException(message="资源不存在")
    
    try:
        credentials = CredentialService.get_ssh_credentials(resource)
        docker_service = DockerService(credentials)
        docker_service.restart_container(container_id)
        return MessageResponse(message=f"容器 {container_id} 已重启")
    except Exception as e:
        raise InternalServerError(message=str(e))


@router.get("/{resource_id}/containers/{container_id}/logs", response_model=ContainerLogsResponse)
async def get_container_logs(
    resource_id: int,
    container_id: str,
    tail: int = Query(100, ge=10, le=1000, description="Number of lines"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Get container logs"""
    resource = await db.get(Resource, resource_id)
    if not resource:
        raise NotFoundException(message="资源不存在")
    
    try:
        credentials = CredentialService.get_ssh_credentials(resource)
        docker_service = DockerService(credentials)
        logs = docker_service.get_logs(container_id, tail=tail)
        return ContainerLogsResponse(container_id=container_id, logs=logs)
    except Exception as e:
        raise InternalServerError(message=str(e))


@router.delete("/{resource_id}/containers/{container_id}", response_model=MessageResponse)
async def remove_container(
    resource_id: int,
    container_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Remove a container"""
    resource = await db.get(Resource, resource_id)
    if not resource:
        raise NotFoundException(message="资源不存在")
    
    try:
        credentials = CredentialService.get_ssh_credentials(resource)
        docker_service = DockerService(credentials)
        docker_service.remove_container(container_id)
        return MessageResponse(message=f"容器 {container_id} 已删除")
    except Exception as e:
        raise InternalServerError(message=str(e))

