from typing import Optional, List, Dict, Any
from enum import Enum
from fastapi import APIRouter, Query, status, Depends
from fastapi.concurrency import run_in_threadpool
import httpx
import os
import re
import socket
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urlparse, urlunparse
from jinja2 import Environment, FileSystemLoader
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_async_db
from app.models.task import Task, TaskStatus
from app.models.resource import Resource
from app.models.user import User
from app.tasks.automation import run_automation_task
from app.core.exceptions import InternalServerError, NotFoundException, BadRequestException
from app.api.v1.auth import get_current_active_user

router = APIRouter()

def get_local_ip(target_ip=None):
    """Get the local IP address that can reach the target_ip"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Use target_ip to find the routing interface, fallback to 8.8.8.8
        connect_to = target_ip if target_ip else "8.8.8.8"
        s.connect((connect_to, 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def parse_iso_to_nanoseconds(iso_str: Optional[str]) -> Optional[int]:
    """Parse ISO 8601 string to nanoseconds timestamp"""
    if not iso_str:
        return None
    try:
        # Handle 'Z' suffix
        clean_str = iso_str.replace('Z', '+00:00')
        dt = datetime.fromisoformat(clean_str)
        # Ensure it has timezone info
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp() * 1e9)
    except Exception:
        return None

class LogDirection(str, Enum):
    FORWARD = "forward"
    BACKWARD = "backward"

@router.get("/search", response_model=Dict[str, Any])
async def search_logs(
    query: str = Query(..., description="Loki LogQL query"),
    start: Optional[str] = Query(None, description="Start time (ISO string or nanoseconds)"),
    end: Optional[str] = Query(None, description="End time (ISO string or nanoseconds)"),
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
        "direction": direction.value
    }
    
    # Convert start/end to nanoseconds if they are ISO strings
    if start:
        if start.isdigit():
            params["start"] = start
        else:
            ts = parse_iso_to_nanoseconds(start)
            if ts: params["start"] = ts
            
    if end:
        if end.isdigit():
            params["end"] = end
        else:
            ts = parse_iso_to_nanoseconds(end)
            if ts: params["end"] = ts

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
                raise InternalServerError(
                    message=f"Loki error: {response.text}"
                )
                
            return response.json()
            
        except httpx.RequestError as exc:
            raise InternalServerError(
                message=f"Could not connect to Loki: {str(exc)}"
            )

@router.get("/labels", response_model=Dict[str, Any])
async def get_labels(
    start: Optional[str] = Query(None, description="Start time in nanoseconds"),
    end: Optional[str] = Query(None, description="End time in nanoseconds")
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
                raise InternalServerError(
                    message=f"Loki error: {response.text}"
                )
                
            return response.json()
            
        except httpx.RequestError as exc:
            raise InternalServerError(
                message=f"Could not connect to Loki: {str(exc)}"
            )

@router.get("/label/{name}/values", response_model=Dict[str, Any])
async def get_label_values(
    name: str,
    start: Optional[str] = Query(None, description="Start time in nanoseconds"),
    end: Optional[str] = Query(None, description="End time in nanoseconds"),
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
                raise InternalServerError(
                    message=f"Loki error: {response.text}"
                )
                
            return response.json()
            
        except httpx.RequestError as exc:
            raise InternalServerError(
                message=f"Could not connect to Loki: {str(exc)}"
            )

@router.post("/deploy/{resource_id}", status_code=status.HTTP_201_CREATED)
async def deploy_promtail(
    resource_id: int,
    loki_host: Optional[str] = Query(None, description="Loki host IP/hostname reachable from target server"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Deploy Promtail to a target resource.
    Generates a deployment script using Jinja2 and executes it via the automation module.
    """
    resource = await db.get(Resource, resource_id)
    if not resource:
        raise NotFoundException(message="Resource not found")
    
    if not resource.ip_address:
        raise BadRequestException(message="Resource has no IP address")

    # Resolve templates directory
    templates_dir = Path(__file__).resolve().parent.parent.parent / "templates"
    if not templates_dir.exists():
        # Fallback for development environments if structure differs
        templates_dir = Path(os.getcwd()) / "app" / "templates"

    if not templates_dir.exists():
         raise InternalServerError(
            message=f"Templates directory not found at {templates_dir}"
        )

    # Sanitize resource name for shell safety
    # Allow alphanumeric, underscore, and hyphen. Replace others with underscore.
    safe_resource_name = re.sub(r'[^a-zA-Z0-9_-]', '_', str(resource.name))
    if not safe_resource_name:
        safe_resource_name = f"resource_{resource.id}"

    # Determine reachable Loki URL for remote Promtail deployment
    # Priority: loki_host (from frontend) > LOKI_EXTERNAL_URL > auto-detect
    if loki_host and loki_host not in ("localhost", "127.0.0.1", "0.0.0.0"):
        loki_url = f"http://{loki_host}:3100"
    elif settings.LOKI_EXTERNAL_URL:
        loki_url = settings.LOKI_EXTERNAL_URL
    else:
        loki_url = settings.LOKI_URL
        parsed_loki = urlparse(loki_url)
        if parsed_loki.hostname in ("loki", "localhost", "127.0.0.1"):
            ext_url = urlparse(settings.EXTERNAL_API_URL)
            host = ext_url.hostname
            if not host or host in ("localhost", "127.0.0.1", "0.0.0.0"):
                host = get_local_ip(resource.ip_address)
            if host and host not in ("localhost", "127.0.0.1", "0.0.0.0"):
                new_netloc = f"{host}:3100"
                loki_url = urlunparse(parsed_loki._replace(netloc=new_netloc))

    try:
        env = Environment(loader=FileSystemLoader(str(templates_dir)))
        template = env.get_template("deploy_promtail.sh.j2")
        
        script_content = await run_in_threadpool(
            template.render,
            loki_url=loki_url,
            host_ip=resource.ip_address,
            resource_name=safe_resource_name
        )
    except Exception as e:
        raise InternalServerError(message=f"Failed to render deployment template: {str(e)}")

    task = Task(
        name=f"Deploy Promtail to {resource.name}",
        description=f"Auto-generated task to deploy Promtail to {resource.name} ({resource.ip_address})",
        task_type="script",
        script_content=script_content,
        target_resources=[resource.id],
        status=TaskStatus.PENDING
    )
    
    db.add(task)
    await db.commit()
    await db.refresh(task)
    
    try:
        run_automation_task.delay(task.id)
    except Exception as e:
        task.status = TaskStatus.FAILED
        task.last_error = f"Failed to queue task: {str(e)}"
        await db.commit()
        raise InternalServerError(message=f"Failed to queue deployment task: {str(e)}")
    
    return {
        "task_id": task.id,
        "message": "Promtail deployment started",
        "status": "pending"
    }
