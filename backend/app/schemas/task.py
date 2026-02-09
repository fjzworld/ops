from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.models.task import TaskStatus


class TaskBase(BaseModel):
    """Base task schema"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    task_type: str = Field(..., max_length=50)  # script, ansible, terraform
    script_content: Optional[str] = None
    script_path: Optional[str] = Field(None, max_length=255)
    parameters: Dict[str, Any] = {}
    target_resources: List[int] = []  # List of resource IDs
    schedule: Optional[str] = Field(None, max_length=100)  # Cron expression
    enabled: bool = True


class TaskCreate(TaskBase):
    """Schema for creating a task"""
    pass


class TaskUpdate(BaseModel):
    """Schema for updating a task"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    task_type: Optional[str] = Field(None, max_length=50)
    script_content: Optional[str] = None
    script_path: Optional[str] = Field(None, max_length=255)
    parameters: Optional[Dict[str, Any]] = None
    target_resources: Optional[List[int]] = None
    schedule: Optional[str] = Field(None, max_length=100)
    enabled: Optional[bool] = None
    status: Optional[TaskStatus] = None


class TaskInDB(TaskBase):
    """Schema for task in database"""
    id: int
    status: TaskStatus
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    execution_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    last_output: Optional[str] = None
    last_error: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None

    class Config:
        from_attributes = True


class TaskExecutionMessage(BaseModel):
    """Schema for manual task execution response"""
    message: str
    task_id: int
