from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List
from app.core.database import get_async_db
from app.models.user import User
from app.models.task import Task, TaskStatus, TaskExecution
from app.api.v1.auth import get_current_active_user
from app.schemas.task import TaskCreate, TaskUpdate, TaskInDB, TaskExecutionMessage
from app.schemas.task_execution import TaskExecutionInDB
from app.tasks.automation import run_automation_task
from app.services.scheduler import SchedulerService
from app.core.exceptions import NotFoundException, PermissionDeniedException, BadRequestException, InternalServerError

router = APIRouter()


@router.get("/tasks", response_model=List[TaskInDB])
async def list_tasks(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db)
):
    """List all automation tasks"""
    result = await db.execute(select(Task).options(selectinload(Task.executions)))
    tasks = result.scalars().all()
    return tasks


@router.get("/tasks/{task_id}", response_model=TaskInDB)
async def get_task(
    task_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Get task by ID with executions"""
    result = await db.execute(
        select(Task)
        .filter(Task.id == task_id)
        .options(selectinload(Task.executions))
    )
    task = result.scalars().first()
    if not task:
        raise NotFoundException(message="Task not found")
    
    return task


@router.post("/tasks", response_model=TaskInDB, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_in: TaskCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Create a new automation task"""
    if current_user.role not in ["admin", "operator"]:
        raise PermissionDeniedException(message="Not enough permissions")
    
    # Validate cron schedule
    if task_in.schedule:
        try:
            SchedulerService.validate_cron(task_in.schedule)
        except ValueError as e:
            raise BadRequestException(message=str(e))
    
    task = Task(
        **task_in.model_dump(),
        created_by=current_user.username
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    
    # Sync with scheduler
    try:
        SchedulerService.sync_task(task)
    except Exception as e:
        raise InternalServerError(message=f"Task created but failed to schedule: {str(e)}")
    
    return task


@router.put("/tasks/{task_id}", response_model=TaskInDB)
async def update_task(
    task_id: int,
    task_in: TaskUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Update an automation task"""
    if current_user.role not in ["admin", "operator"]:
        raise PermissionDeniedException(message="Not enough permissions")
    
    task = await db.get(Task, task_id)
    if not task:
        raise NotFoundException(message="Task not found")
    
    # Validate cron schedule if provided
    if task_in.schedule is not None:
        try:
            SchedulerService.validate_cron(task_in.schedule)
        except ValueError as e:
            raise BadRequestException(message=str(e))
    
    update_data = task_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(task, field, value)
    
    await db.commit()
    await db.refresh(task)
    
    # Sync with scheduler
    try:
        SchedulerService.sync_task(task)
    except Exception as e:
        raise InternalServerError(message=f"Task updated but failed to sync schedule: {str(e)}")
    
    return task


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Delete an automation task"""
    if current_user.role != "admin":
        raise PermissionDeniedException(message="Only admin can delete tasks")
    
    task = await db.get(Task, task_id)
    if not task:
        raise NotFoundException(message="Task not found")
    
    # Sync with scheduler (delete)
    try:
        SchedulerService.delete_task(task_id)
    except Exception as e:
        raise InternalServerError(message=f"Failed to remove task from scheduler: {str(e)}")

    await db.delete(task)
    await db.commit()
    return None


@router.post("/tasks/{task_id}/execute", response_model=TaskExecutionMessage)
async def execute_task(
    task_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Execute a task manually"""
    if current_user.role not in ["admin", "operator"]:
        raise PermissionDeniedException(message="Not enough permissions")
    
    task = await db.get(Task, task_id)
    if not task:
        raise NotFoundException(message="Task not found")
    
    # Update task status to RUNNING
    task.status = TaskStatus.RUNNING
    await db.commit()
    
    # Trigger appropriate Celery task based on task type
    if task.task_type == "deploy_alloy":
        # For deployment tasks, we need to pass additional parameters
        # For simplicity, we trigger it with default settings or existing credentials
        from app.tasks.deployment import deploy_alloy_task
        from app.core.config import settings
        
        resource_id = task.target_resources[0] if task.target_resources else None
        if not resource_id:
            raise BadRequestException(message="Deployment task has no target resource")
            
        deploy_alloy_task.delay(
            task.id,
            resource_id,
            settings.EXTERNAL_API_URL
        )
    else:
        run_automation_task.delay(task_id)
    
    return {"message": "Task execution queued", "task_id": task_id}


@router.get("/tasks/{task_id}/executions", response_model=List[TaskExecutionInDB])
async def list_task_executions(
    task_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db)
):
    """List execution history for a specific task"""
    task = await db.get(Task, task_id)
    if not task:
        raise NotFoundException(message="Task not found")
    
    result = await db.execute(
        select(TaskExecution)
        .filter(TaskExecution.task_id == task_id)
        .order_by(TaskExecution.start_time.desc())
    )
    executions = result.scalars().all()
    return executions


@router.get("/executions/{execution_id}", response_model=TaskExecutionInDB)
async def get_execution_details(
    execution_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Get details of a specific execution"""
    execution = await db.get(TaskExecution, execution_id)
    if not execution:
        raise NotFoundException(message="Execution not found")
    
    return execution
