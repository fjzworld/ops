import logging
from typing import List
from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_db
from app.models.user import User
from app.models.resource import Resource
from app.api.v1.auth import get_current_active_user
from app.core.exceptions import (
    NotFoundException, PermissionDeniedException, BadRequestException, InternalServerError
)
from app.schemas.deploy import (
    DeployExecuteRequest, DeployRollbackRequest, DeployResponse,
    UploadResponse, BackupInfo
)
from app.services.deploy_service import DeployService

logger = logging.getLogger(__name__)

router = APIRouter()

MAX_UPLOAD_SIZE = 100 * 1024 * 1024  # 100MB


@router.post("/frontend/upload", response_model=UploadResponse)
async def upload_dist_package(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
):
    """Upload a frontend dist package (zip or tar.gz)"""
    if current_user.role != "admin":
        raise PermissionDeniedException(message="Only admin can deploy")

    if not file.filename:
        raise BadRequestException(message="No file provided")

    filename = file.filename.lower()
    if not (filename.endswith('.zip') or filename.endswith('.tar.gz') or filename.endswith('.tgz')):
        raise BadRequestException(message="Only .zip and .tar.gz files are supported")

    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE:
        raise BadRequestException(message=f"File too large. Maximum size is {MAX_UPLOAD_SIZE // 1024 // 1024}MB")

    try:
        file_id, saved_path = DeployService.save_upload(content, file.filename)
    except ValueError as e:
        raise BadRequestException(message=str(e))

    valid, message = DeployService.validate_package(saved_path)
    if not valid:
        DeployService.cleanup_upload(file_id)
        raise BadRequestException(message=message)

    return UploadResponse(
        file_id=file_id,
        filename=file.filename,
        size=len(content),
        valid=True,
        message="Package uploaded and validated successfully"
    )


@router.post("/frontend/execute", response_model=DeployResponse)
async def execute_deploy(
    request: DeployExecuteRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Execute frontend deployment to selected servers"""
    if current_user.role != "admin":
        raise PermissionDeniedException(message="Only admin can deploy")

    file_path = DeployService.get_upload_path(request.file_id)
    if not file_path:
        raise NotFoundException(message="Uploaded file not found or expired")

    resources = []
    for rid in request.resource_ids:
        resource = await db.get(Resource, rid)
        if not resource:
            raise NotFoundException(message=f"Resource {rid} not found")
        if not resource.ip_address:
            raise BadRequestException(message=f"Resource {resource.name} has no IP address")
        resources.append(resource)

    try:
        results = await DeployService.deploy_to_servers(
            file_path, resources, request.restart_keepalived
        )
    except Exception as e:
        logger.error(f"Deployment failed: {e}")
        raise InternalServerError(message=f"Deployment failed: {str(e)}")
    finally:
        DeployService.cleanup_upload(request.file_id)

    overall_success = all(r.success for r in results)
    return DeployResponse(success=overall_success, results=results)


@router.get("/frontend/backups", response_model=List[BackupInfo])
async def get_backups(
    resource_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Get backup list from a target server"""
    if current_user.role != "admin":
        raise PermissionDeniedException(message="Only admin can view backups")

    resource = await db.get(Resource, resource_id)
    if not resource:
        raise NotFoundException(message="Resource not found")

    try:
        backups = await DeployService.get_backups(resource)
        return [BackupInfo(**b) for b in backups]
    except Exception as e:
        raise InternalServerError(message=f"Failed to get backups: {str(e)}")


@router.post("/frontend/rollback", response_model=DeployResponse)
async def rollback_deploy(
    request: DeployRollbackRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Rollback to a specific backup version"""
    if current_user.role != "admin":
        raise PermissionDeniedException(message="Only admin can rollback")

    resource = await db.get(Resource, request.resource_id)
    if not resource:
        raise NotFoundException(message="Resource not found")

    result = await DeployService.rollback(resource, request.backup_name)
    return DeployResponse(success=result.success, results=[result])
