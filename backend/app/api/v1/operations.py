import os
import logging
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query, UploadFile, File, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_async_db
from app.models.user import User
from app.models.operation import Operation, OperationType, OperationStatus, OperationExecution
from app.models.resource import Resource
from app.api.v1.auth import get_current_active_user
from app.schemas.operation import (
    OperationCreate, OperationUpdate, OperationInDB,
    OperationExecuteMessage, OperationExecutionInDB, DeployExecuteRequest
)
from app.schemas.deploy import UploadResponse, BackupInfo, DeployResponse, DeployRollbackRequest
from app.tasks.automation import run_automation_task
from app.services.scheduler import SchedulerService
from app.services.deploy_service import DeployService
from app.core.exceptions import (
    NotFoundException, PermissionDeniedException, BadRequestException, InternalServerError
)

logger = logging.getLogger(__name__)
router = APIRouter()

MAX_UPLOAD_SIZE = 100 * 1024 * 1024  # 100MB


# ========== Generic Operation CRUD ==========

@router.get("", response_model=List[OperationInDB])
async def list_operations(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    operation_type: Optional[OperationType] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db)
):
    """List operations with optional type filter"""
    query = select(Operation).options(selectinload(Operation.executions))
    if operation_type:
        query = query.filter(Operation.operation_type == operation_type)
    query = query.order_by(Operation.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{operation_id}", response_model=OperationInDB)
async def get_operation(
    operation_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Get operation by ID with executions"""
    result = await db.execute(
        select(Operation).filter(Operation.id == operation_id)
        .options(selectinload(Operation.executions))
    )
    op = result.scalars().first()
    if not op:
        raise NotFoundException(message="Operation not found")
    return op


@router.post("", response_model=OperationInDB, status_code=status.HTTP_201_CREATED)
async def create_operation(
    op_in: OperationCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Create a new operation"""
    if current_user.role not in ["admin", "operator"]:
        raise PermissionDeniedException(message="Not enough permissions")

    # Validate cron schedule for script_exec
    if op_in.schedule and op_in.operation_type == OperationType.SCRIPT_EXEC:
        try:
            SchedulerService.validate_cron(op_in.schedule)
        except ValueError as e:
            raise BadRequestException(message=str(e))

    operation = Operation(
        **op_in.model_dump(),
        created_by=current_user.username
    )
    db.add(operation)
    await db.commit()
    await db.refresh(operation)

    # Sync with scheduler (only for script_exec)
    if operation.operation_type == OperationType.SCRIPT_EXEC:
        try:
            SchedulerService.sync_task(operation)
        except Exception as e:
            raise InternalServerError(message=f"Operation created but failed to schedule: {str(e)}")

    return operation


@router.put("/{operation_id}", response_model=OperationInDB)
async def update_operation(
    operation_id: int,
    op_in: OperationUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Update an operation"""
    if current_user.role not in ["admin", "operator"]:
        raise PermissionDeniedException(message="Not enough permissions")

    operation = await db.get(Operation, operation_id)
    if not operation:
        raise NotFoundException(message="Operation not found")

    if op_in.schedule is not None and operation.operation_type == OperationType.SCRIPT_EXEC:
        try:
            SchedulerService.validate_cron(op_in.schedule)
        except ValueError as e:
            raise BadRequestException(message=str(e))

    update_data = op_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(operation, field, value)

    await db.commit()
    await db.refresh(operation)

    if operation.operation_type == OperationType.SCRIPT_EXEC:
        try:
            SchedulerService.sync_task(operation)
        except Exception as e:
            raise InternalServerError(message=f"Updated but failed to sync schedule: {str(e)}")

    return operation


@router.delete("/{operation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_operation(
    operation_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Delete an operation"""
    if current_user.role != "admin":
        raise PermissionDeniedException(message="Only admin can delete")

    operation = await db.get(Operation, operation_id)
    if not operation:
        raise NotFoundException(message="Operation not found")

    if operation.operation_type == OperationType.SCRIPT_EXEC:
        try:
            SchedulerService.delete_task(operation_id)
        except Exception as e:
            raise InternalServerError(message=f"Failed to remove from scheduler: {str(e)}")

    await db.delete(operation)
    await db.commit()
    return None


# ========== Script Execution ==========

@router.post("/{operation_id}/execute", response_model=OperationExecuteMessage)
async def execute_operation(
    operation_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Execute a script_exec operation manually"""
    if current_user.role not in ["admin", "operator"]:
        raise PermissionDeniedException(message="Not enough permissions")

    operation = await db.get(Operation, operation_id)
    if not operation:
        raise NotFoundException(message="Operation not found")

    if operation.operation_type != OperationType.SCRIPT_EXEC:
        raise BadRequestException(message="Only script_exec operations can be executed this way")

    operation.status = OperationStatus.RUNNING
    await db.commit()

    # Check for deploy_alloy special case
    config = operation.config or {}
    if config.get("task_type") == "deploy_alloy":
        from app.tasks.deployment import deploy_alloy_task
        from app.core.config import settings
        resource_id = operation.target_resources[0] if operation.target_resources else None
        if not resource_id:
            raise BadRequestException(message="Deployment task has no target resource")
        deploy_alloy_task.delay(operation.id, resource_id, settings.EXTERNAL_API_URL)
    else:
        run_automation_task.delay(operation_id)

    return {"message": "Operation execution queued", "operation_id": operation_id}


# ========== Execution History ==========

@router.get("/{operation_id}/executions", response_model=List[OperationExecutionInDB])
async def list_executions(
    operation_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db)
):
    """List execution history for an operation"""
    operation = await db.get(Operation, operation_id)
    if not operation:
        raise NotFoundException(message="Operation not found")

    result = await db.execute(
        select(OperationExecution)
        .filter(OperationExecution.operation_id == operation_id)
        .order_by(OperationExecution.start_time.desc())
    )
    return result.scalars().all()


@router.get("/executions/{execution_id}", response_model=OperationExecutionInDB)
async def get_execution_details(
    execution_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Get details of a specific execution"""
    execution = await db.get(OperationExecution, execution_id)
    if not execution:
        raise NotFoundException(message="Execution not found")
    return execution


# ========== Deploy Endpoints ==========

@router.post("/deploy/upload", response_model=UploadResponse)
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
        file_id=file_id, filename=file.filename,
        size=len(content), valid=True,
        message="Package uploaded and validated successfully"
    )


@router.post("/deploy/execute", response_model=DeployResponse)
async def execute_deploy(
    request: DeployExecuteRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Execute frontend deployment — creates Operation record with execution history"""
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

    # Create Operation record for this deployment
    operation = Operation(
        name=f"前端部署 {os.path.basename(file_path)}",
        description=f"部署到 {', '.join(r.name for r in resources)}",
        operation_type=OperationType.FRONTEND_DEPLOY,
        config={
            "restart_keepalived": request.restart_keepalived,
            "filename": os.path.basename(file_path),
        },
        target_resources=request.resource_ids,
        status=OperationStatus.RUNNING,
        execution_count=1,
        last_run_at=datetime.now(timezone.utc),
        created_by=current_user.username,
    )
    db.add(operation)
    await db.commit()
    await db.refresh(operation)

    try:
        results = await DeployService.deploy_to_servers(
            file_path, resources, request.restart_keepalived
        )
    except Exception as e:
        logger.error(f"Deployment failed: {e}")
        operation.status = OperationStatus.FAILED
        operation.last_error = str(e)
        operation.failure_count += 1
        await db.commit()
        raise InternalServerError(message=f"Deployment failed: {str(e)}")
    finally:
        DeployService.cleanup_upload(request.file_id)

    # Update operation status
    overall_success = all(r.success for r in results)
    operation.status = OperationStatus.SUCCESS if overall_success else OperationStatus.FAILED
    if overall_success:
        operation.success_count += 1
    else:
        operation.failure_count += 1
    operation.last_output = "\n".join(
        f"[{r.server}] {'成功' if r.success else '失败'}" for r in results
    )
    if not overall_success:
        operation.last_error = "; ".join(r.error for r in results if r.error)

    # Save execution record
    execution = OperationExecution(
        operation_id=operation.id,
        operation_type=OperationType.FRONTEND_DEPLOY,
        status=OperationStatus.SUCCESS if overall_success else OperationStatus.FAILED,
        start_time=operation.last_run_at,
        end_time=datetime.now(timezone.utc),
        steps=[s.model_dump() for r in results for s in r.steps],
        input_data={
            "file_id": request.file_id,
            "resource_ids": request.resource_ids,
            "restart_keepalived": request.restart_keepalived,
        },
    )
    db.add(execution)
    await db.commit()

    return DeployResponse(success=overall_success, results=results)


@router.get("/deploy/backups", response_model=List[BackupInfo])
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


@router.post("/deploy/rollback", response_model=DeployResponse)
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
