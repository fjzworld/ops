from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.task import TaskStatus


class TaskExecutionInDB(BaseModel):
    id: int
    task_id: int
    status: TaskStatus
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    output: Optional[str] = None
    error: Optional[str] = None

    class Config:
        from_attributes = True
