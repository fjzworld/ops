from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime
from app.models.resource import ResourceType, ResourceStatus


class ResourceBase(BaseModel):
    """Base resource schema"""
    name: str = Field(..., min_length=1, max_length=100)
    type: ResourceType
    ip_address: Optional[str] = None
    hostname: Optional[str] = None
    cpu_cores: Optional[int] = Field(None, ge=1)
    memory_gb: Optional[float] = Field(None, ge=0)
    disk_gb: Optional[float] = Field(None, ge=0)
    os_type: Optional[str] = None
    os_version: Optional[str] = None
    tags: List[str] = []
    labels: Dict[str, str] = {}
    description: Optional[str] = None


class ResourceCreate(ResourceBase):
    """Schema for creating a resource"""
    # SSH credentials for auto-discovery and management
    ssh_port: int = Field(22, ge=1, le=65535)
    ssh_username: Optional[str] = "root"
    ssh_password: Optional[str] = None
    ssh_private_key: Optional[str] = None
    backend_url: Optional[str] = Field(None, description="Backend URL for agent to connect back")
    
    # Override base fields to be optional (auto-detected if not provided)
    cpu_cores: Optional[int] = None
    memory_gb: Optional[float] = None
    disk_gb: Optional[float] = None
    os_type: Optional[str] = None


class ResourceUpdate(BaseModel):
    """Schema for updating a resource"""
    name: Optional[str] = None
    status: Optional[ResourceStatus] = None
    ip_address: Optional[str] = None
    hostname: Optional[str] = None
    cpu_cores: Optional[int] = None
    memory_gb: Optional[float] = None
    disk_gb: Optional[float] = None
    os_type: Optional[str] = None
    os_version: Optional[str] = None
    tags: Optional[List[str]] = None
    labels: Optional[Dict[str, str]] = None
    description: Optional[str] = None


class ResourceInDB(ResourceBase):
    """Schema for resource in database"""
    id: int
    status: ResourceStatus
    cpu_usage: Optional[float] = 0.0
    memory_usage: Optional[float] = 0.0
    disk_usage: Optional[float] = 0.0
    network_in: Optional[float] = 0.0
    network_out: Optional[float] = 0.0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    has_credentials: bool = False
    
    class Config:
        from_attributes = True


class DiskPartition(BaseModel):
    """Single disk partition info"""
    mountpoint: str
    device: str
    fstype: str
    total_gb: float
    used_gb: float
    percent: float


class ResourceMetrics(BaseModel):
    """Resource metrics update"""
    cpu_usage: float = Field(..., ge=0, le=100)
    memory_usage: float = Field(..., ge=0, le=100)
    disk_usage: float = Field(..., ge=0, le=100)
    disk_partitions: Optional[List[DiskPartition]] = None
    network_in: Optional[float] = Field(0, ge=0)
    network_out: Optional[float] = Field(0, ge=0)
    top_processes: Optional[List[Dict]] = []


class ResourceProbeRequest(BaseModel):
    """Request to probe a server for auto-detection"""
    ip_address: str = Field(..., description="Server IP address")
    ssh_port: int = Field(22, ge=1, le=65535)
    ssh_username: str = Field(..., min_length=1)
    ssh_password: Optional[str] = None
    ssh_private_key: Optional[str] = None
    backend_url: Optional[str] = Field(None, description="Custom backend URL for agent callbacks")


class ResourceProbeResponse(BaseModel):
    """Response from server probe"""
    hostname: str
    cpu_cores: int
    memory_gb: float
    disk_gb: float
    os_type: str
    os_version: str
    kernel_version: str


class ResourceDeleteRequest(BaseModel):
    """Request to delete a resource with optional agent uninstall"""
    uninstall_agent: bool = Field(True, description="Whether to uninstall agent from remote server")
    ssh_port: int = Field(22, ge=1, le=65535)
    ssh_username: str = Field("root", min_length=1)
    ssh_password: Optional[str] = None
    ssh_private_key: Optional[str] = None


class ResourceStats(BaseModel):
    """Resource statistics summary"""
    total: int
    active: int
    inactive: int
    by_type: Dict[str, int]


class MessageResponse(BaseModel):
    """Generic message response schema"""
    message: str


class MetricResponse(BaseModel):
    """Resource metrics response"""
    resource_id: int
    metrics: List[Dict]
    processes: List[Dict]


class ResourceImportResult(BaseModel):
    """Result of bulk resource import"""
    total: int
    success: int
    failed: int
    errors: List[str]
    tasks_triggered: int
