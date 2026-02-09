from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.models.user import User
from app.models.task import Task, TaskStatus, TaskExecution
from app.api.v1.auth import get_current_active_user
from app.schemas.task import TaskCreate, TaskUpdate, TaskInDB, TaskExecutionMessage
from app.schemas.task_execution import TaskExecutionInDB
from app.tasks.automation import run_automation_task
from app.services.scheduler import SchedulerService

router = APIRouter()


@router.get("/tasks", response_model=List[TaskInDB])
def list_tasks(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List all automation tasks"""
    tasks = db.query(Task).all()
    return tasks


@router.get("/tasks/{task_id}", response_model=TaskInDB)
def get_task(
    task_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get task by ID"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    return task


@router.post("/tasks", response_model=TaskInDB, status_code=status.HTTP_201_CREATED)
def create_task(
    task_in: TaskCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new automation task"""
    if current_user.role not in ["admin", "operator"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Validate cron schedule
    if task_in.schedule:
        try:
            SchedulerService.validate_cron(task_in.schedule)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
    
    task = Task(
        **task_in.model_dump(),
        created_by=current_user.username
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    
    # Sync with scheduler
    try:
        SchedulerService.sync_task(task)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Task created but failed to schedule: {str(e)}"
        )
    
    return task


@router.put("/tasks/{task_id}", response_model=TaskInDB)
def update_task(
    task_id: int,
    task_in: TaskUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update an automation task"""
    if current_user.role not in ["admin", "operator"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    # Validate cron schedule if provided
    if task_in.schedule is not None:
        try:
            SchedulerService.validate_cron(task_in.schedule)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
    
    update_data = task_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(task, field, value)
    
    db.commit()
    db.refresh(task)
    
    # Sync with scheduler
    try:
        SchedulerService.sync_task(task)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Task updated but failed to sync schedule: {str(e)}"
        )
    
    return task


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete an automation task"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin can delete tasks"
        )
    
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    # Sync with scheduler (delete)
    try:
        SchedulerService.delete_task(task_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to remove task from scheduler: {str(e)}"
        )

    db.delete(task)
    db.commit()
    return None


@router.post("/tasks/{task_id}/execute", response_model=TaskExecutionMessage)
def execute_task(
    task_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Execute a task manually"""
    if current_user.role not in ["admin", "operator"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    # Update task status to RUNNING
    task.status = TaskStatus.RUNNING
    db.commit()
    
    # Trigger Celery task
    run_automation_task.delay(task_id)
    
    return {"message": "Task execution queued", "task_id": task_id}


@router.get("/tasks/{task_id}/executions", response_model=List[TaskExecutionInDB])
def list_task_executions(
    task_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List execution history for a specific task"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    executions = db.query(TaskExecution).filter(TaskExecution.task_id == task_id).order_by(TaskExecution.start_time.desc()).all()
    return executions


@router.get("/executions/{execution_id}", response_model=TaskExecutionInDB)
def get_execution_details(
    execution_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get details of a specific execution"""
    execution = db.query(TaskExecution).filter(TaskExecution.id == execution_id).first()
    if not execution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Execution not found"
        )
    
    return execution
