from pydantic import BaseModel, Field
from typing import List, Optional


class DeployExecuteRequest(BaseModel):
    """Request to execute frontend deployment"""

    file_id: str = Field(..., description="Uploaded file ID from upload endpoint")
    resource_ids: List[int] = Field(
        ..., min_length=1, description="Target resource IDs from CMDB"
    )
    restart_keepalived: bool = Field(
        default=False,
        description="Whether to restart keepalived (for 2-server HA frontend)",
    )
    restart_container: bool = Field(
        default=True,
        description="Whether to restart container after backend/algorithm deploy",
    )
    restart_container: bool = Field(
        default=True, description="Whether to restart container after deploy"
    )


class DeployRollbackRequest(BaseModel):
    """Request to rollback to a backup"""

    resource_id: int
    deploy_type: str = Field(
        default="frontend", description="Type of deployment to determine paths"
    )
    backup_name: str = Field(
        ..., description="Backup filename like html_20260226_110000.tar.gz"
    )


class DeployStepLog(BaseModel):
    """Single step log entry"""

    server: str
    step: str
    status: str  # "success" | "failed" | "running"
    message: str = ""


class DeployResult(BaseModel):
    """Deployment result for one server"""

    server: str
    resource_id: int
    success: bool
    steps: List[DeployStepLog] = []
    error: Optional[str] = None


class DeployResponse(BaseModel):
    """Overall deployment response"""

    success: bool
    results: List[DeployResult]


class BackupInfo(BaseModel):
    """Backup file information"""

    name: str
    size: str
    created_at: str


class UploadResponse(BaseModel):
    """Upload response"""

    file_id: str
    filename: str
    deploy_type: str = "frontend"
    size: int
    valid: bool
    message: str
