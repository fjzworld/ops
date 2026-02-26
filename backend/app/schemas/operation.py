from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.models.operation import OperationType, OperationStatus


# --- Base schemas ---

class OperationBase(BaseModel):
    """Base operation schema"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    operation_type: OperationType
    config: Dict[str, Any] = {}
    target_resources: List[int] = []
    schedule: Optional[str] = Field(None, max_length=100)
    enabled: bool = True


class OperationCreate(OperationBase):
    """Schema for creating an operation"""
    pass


class OperationUpdate(BaseModel):
    """Schema for updating an operation"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    config: Optional[Dict[str, Any]] = None
    target_resources: Optional[List[int]] = None
    schedule: Optional[str] = Field(None, max_length=100)
    enabled: Optional[bool] = None
    status: Optional[OperationStatus] = None


class OperationInDB(OperationBase):
    """Schema for operation in database"""
    id: int
    status: OperationStatus
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


# --- Execution schemas ---

class OperationExecutionInDB(BaseModel):
    """Schema for operation execution history"""
    id: int
    operation_id: int
    operation_type: OperationType
    status: OperationStatus
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    output: Optional[str] = None
    error: Optional[str] = None
    steps: List[Dict[str, Any]] = []
    input_data: Dict[str, Any] = {}

    class Config:
        from_attributes = True


# --- Action schemas ---

class OperationExecuteMessage(BaseModel):
    """Response for manual operation execution"""
    message: str
    operation_id: int


class DeployExecuteRequest(BaseModel):
    """Request to execute frontend deployment via operation"""
    file_id: str = Field(..., description="Uploaded file ID")
    resource_ids: List[int] = Field(..., min_length=1, max_length=2)
    restart_keepalived: bool = False
