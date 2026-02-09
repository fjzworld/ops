from typing import Optional, Literal
from datetime import datetime
from pydantic import BaseModel

# Simple nested schema for resource association
class ResourceBrief(BaseModel):
    id: int
    name: str
    ip_address: Optional[str] = None
    
    class Config:
        from_attributes = True

class MiddlewareBase(BaseModel):
    name: str
    type: str
    resource_id: int
    port: int
    username: Optional[str] = None
    service_name: Optional[str] = None
    log_path: Optional[str] = None

class MiddlewareCreate(MiddlewareBase):
    password_plain: Optional[str] = None

class MiddlewareUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    resource_id: Optional[int] = None
    port: Optional[int] = None
    username: Optional[str] = None
    password_plain: Optional[str] = None
    service_name: Optional[str] = None
    log_path: Optional[str] = None
    status: Optional[str] = None

class MiddlewareAction(BaseModel):
    action: Literal["start", "stop", "restart"]

class MiddlewareInDB(MiddlewareBase):
    id: int
    status: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    resource: Optional[ResourceBrief] = None

    class Config:
        from_attributes = True
