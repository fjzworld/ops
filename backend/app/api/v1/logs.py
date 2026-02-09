from typing import Optional, List, Dict, Any
from enum import Enum
from fastapi import APIRouter, HTTPException, Query, status, Depends
import httpx
import os
import re
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.task import Task, TaskStatus
from app.models.resource import Resource
from app.tasks.automation import run_automation_task

router = APIRouter()

class LogDirection(str, Enum):
    FORWARD = "FORWARD"
    BACKWARD = "BACKWARD"

@router.get("/search", response_model=Dict[str, Any])
async def search_logs(
    query: str = Query(..., description="Loki LogQL query"),
    start: Optional[int] = Query(None, description="Start time in nanoseconds"),
    end: Optional[int] = Query(None, description="End time in nanoseconds"),
    limit: int = Query(1000, le=5000, description="Max logs to return"),
    direction: LogDirection = Query(LogDirection.BACKWARD, description="Order (FORWARD or BACKWARD)"),
    step: Optional[str] = Query(None, description="Query resolution step width"),
):
    """
    Search logs in Loki using LogQL
    """
    params = {
        "query": query,
        "limit": limit,
        "direction": direction
    }
    
    if start:
        params["start"] = start
    if end:
        params["end"] = end
    if step:
        params["step"] = step

    async with httpx.AsyncClient() as client:
        try:
            # Proxy request to Loki
            response = await client.get(
                f"{settings.LOKI_URL}/loki/api/v1/query_range",
                params=params,
                timeout=30.0
            )
            
            # Forward Loki status code if error
            if response.is_error:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Loki error: {response.text}"
                )
                
            return response.json()
            
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Could not connect to Loki: {str(exc)}"
            )

@router.get("/labels", response_model=Dict[str, Any])
async def get_labels(
    start: Optional[int] = Query(None, description="Start time in nanoseconds"),
    end: Optional[int] = Query(None, description="End time in nanoseconds")
):
    """
    Get all available labels
    """
    params = {}
    if start:
        params["start"] = start
    if end:
        params["end"] = end
        
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{settings.LOKI_URL}/loki/api/v1/labels",
                params=params,
                timeout=10.0
            )
            
            if response.is_error:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Loki error: {response.text}"
                )
                
            return response.json()
            
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Could not connect to Loki: {str(exc)}"
            )

@router.get("/label/{name}/values", response_model=Dict[str, Any])
async def get_label_values(
    name: str,
    start: Optional[int] = Query(None, description="Start time in nanoseconds"),
    end: Optional[int] = Query(None, description="End time in nanoseconds"),
    query: Optional[str] = Query(None, description="LogQL query to filter label values")
):
    """
    Get values for a specific label
    """
    params = {}
    if start:
        params["start"] = start
    if end:
        params["end"] = end
    if query:
        params["query"] = query
        
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{settings.LOKI_URL}/loki/api/v1/label/{name}/values",
                params=params,
                timeout=10.0
            )
            
            if response.is_error:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Loki error: {response.text}"
                )
                
            return response.json()
            
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Could not connect to Loki: {str(exc)}"
            )

@router.post("/deploy/{resource_id}", status_code=status.HTTP_201_CREATED)
async def deploy_promtail(
    resource_id: int,
    db: Session = Depends(get_db)
):
    """
    Deploy Promtail to a target resource.
    Generates a deployment script using Jinja2 and executes it via the automation module.
    """
    resource = db.query(Resource).filter(Resource.id == resource_id).first()
    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found"
        )
    
    if not resource.ip_address:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Resource has no IP address"
        )

    # Resolve templates directory
    templates_dir = Path(__file__).resolve().parent.parent.parent / "templates"
    if not templates_dir.exists():
        # Fallback for development environments if structure differs
        templates_dir = Path(os.getcwd()) / "app" / "templates"

    if not templates_dir.exists():
         raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Templates directory not found at {templates_dir}"
        )

    # Sanitize resource name for shell safety
    # Allow alphanumeric, underscore, and hyphen. Replace others with underscore.
    safe_resource_name = re.sub(r'[^a-zA-Z0-9_-]', '_', resource.name)
    if not safe_resource_name:
        safe_resource_name = f"resource_{resource.id}"

    try:
        env = Environment(loader=FileSystemLoader(str(templates_dir)))
        template = env.get_template("deploy_promtail.sh.j2")
        
        script_content = template.render(
            loki_url=settings.LOKI_URL,
            host_ip=resource.ip_address,
            resource_name=safe_resource_name
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to render deployment template: {str(e)}"
        )

    task = Task(
        name=f"Deploy Promtail to {resource.name}",
        description=f"Auto-generated task to deploy Promtail to {resource.name} ({resource.ip_address})",
        task_type="script",
        script_content=script_content,
        target_resources=[resource.id],
        status=TaskStatus.PENDING
    )
    
    db.add(task)
    db.commit()
    db.refresh(task)
    
    try:
        run_automation_task.delay(task.id)
    except Exception as e:
        task.status = TaskStatus.FAILED
        task.last_error = f"Failed to queue task: {str(e)}"
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to queue deployment task: {str(e)}"
        )
    
    return {
        "task_id": task.id,
        "message": "Promtail deployment started",
        "status": "pending"
    }
