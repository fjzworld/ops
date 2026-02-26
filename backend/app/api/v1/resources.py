import logging
import asyncio
import paramiko
from fastapi import APIRouter, Depends, Query, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta, timezone
from app.core.database import get_async_db
from app.core.exceptions import NotFoundException, BadRequestException, PermissionDeniedException, InternalServerError
from app.models.user import User
from app.models.resource import Resource, ResourceType, ResourceStatus
from app.models.task import Task, TaskStatus
from app.schemas.resource import (
    ResourceCreate, ResourceUpdate, ResourceInDB,
    ResourceProbeRequest, ResourceProbeResponse,
    ResourceDeleteRequest, ResourceStats, MessageResponse, MetricResponse
)
from pydantic import BaseModel
from app.api.v1.auth import get_current_active_user
from app.services.resource_detector import probe_server, SSHCredentials
from app.services.alloy_deployer import deploy_alloy_agent
from app.services.credential_service import CredentialService
from app.tasks.deployment import deploy_alloy_task
from app.core.encryption import encrypt_string
from app.core.monitoring import clear_metrics, update_resource_status
from app.core.config import settings
from app.core.ssh import create_secure_client

from app.core.prometheus import PrometheusClient


logger = logging.getLogger(__name__)

router = APIRouter()


class TaskExecutionMessage(BaseModel):
    """Schema for task execution response"""
    message: str
    task_id: int


@router.get("/", response_model=List[ResourceInDB])
async def list_resources(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=1000),
    resource_type: Optional[ResourceType] = None,
    status: Optional[ResourceStatus] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db)
):
    """List all resources"""
    logger.info(f"LIST_RESOURCES_START: user={current_user.username}, type={resource_type}, status={status}")
    query = select(Resource)
    
    if resource_type:
        query = query.filter(Resource.type == resource_type)
    
    if status:
        query = query.filter(Resource.status == status)
    
    query = query.offset(skip).limit(limit)
    
    result = await db.execute(query)
    resources = result.scalars().all()
    
    logger.info(f"LIST_RESOURCES_END: found {len(resources)} items")
    
    # Set has_credentials flag for all resources
    for res in resources:
        res.has_credentials = bool(res.ssh_password_enc or res.ssh_private_key_enc)
        
    return resources


@router.get("/{resource_id}", response_model=ResourceInDB)
async def get_resource(
    resource_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Get resource by ID"""
    # Optimization: Verified that ResourceInDB schema does not include relationships.
    # Resource.metrics is historical data and should not be loaded unless requested.
    # Resource.alert_rules relationship does not exist on the model.
    # query = select(Resource).options(selectinload(Resource.metrics)).where(Resource.id == resource_id)
    
    result = await db.execute(
        select(Resource)
        .filter(Resource.id == resource_id)
    )
    resource = result.scalars().first()
    if not resource:
        raise NotFoundException(message="Resource not found")
    
    # Set has_credentials flag
    resource.has_credentials = bool(resource.ssh_password_enc or resource.ssh_private_key_enc)
    return resource


@router.post("/", response_model=ResourceInDB, status_code=status.HTTP_201_CREATED)
async def create_resource(
    resource_data: ResourceCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Create a new resource.
    
    If SSH credentials (password or key) are provided:
    1. Probes the server to auto-detect hardware info (CPU, Memory, Disk, OS).
    2. Encrypts and saves credentials.
    3. Auto-deploys the monitoring agent.
    """
    # Check if resource name already exists
    result = await db.execute(select(Resource).filter(Resource.name == resource_data.name))
    if result.scalars().first():
        raise BadRequestException(message="Resource name already exists")
    
    # Check if we should perform auto-discovery
    auto_discovery = False
    probe_info = None
    
    if resource_data.ip_address and (resource_data.ssh_password or resource_data.ssh_private_key):
        auto_discovery = True
        try:
            # 1. Probe Server
            logger.info(f"Auto-probing server: {resource_data.ip_address}")
            credentials = CredentialService.build_ssh_credentials(
                ip_address=resource_data.ip_address,
                port=resource_data.ssh_port,
                username=resource_data.ssh_username,
                password=resource_data.ssh_password,
                private_key=resource_data.ssh_private_key
            )
            probe_info = await run_in_threadpool(probe_server, credentials)
            
            # Update resource data with probed info
            if not resource_data.hostname: resource_data.hostname = probe_info.hostname
            if not resource_data.cpu_cores: resource_data.cpu_cores = probe_info.cpu_cores
            if not resource_data.memory_gb: resource_data.memory_gb = probe_info.memory_gb
            if not resource_data.disk_gb: resource_data.disk_gb = probe_info.disk_gb
            if not resource_data.os_type: resource_data.os_type = f"{probe_info.os_type} {probe_info.os_version}"
            
            # Save kernel version to labels
            if resource_data.labels is None:
                resource_data.labels = {}
            resource_data.labels["kernel_version"] = probe_info.kernel_version
            
        except Exception as e:
            # If probing fails, we abort creation because the credentials might be wrong
            raise BadRequestException(message=f"Server connection failed: {str(e)}")

    # Prepare DB object
    db_resource_dict = resource_data.dict(exclude={
        "ssh_password", "ssh_private_key", "backend_url"
    })
    
    # Add encrypted credentials if available
    if resource_data.ssh_password:
        db_resource_dict["ssh_password_enc"] = encrypt_string(resource_data.ssh_password)
    if resource_data.ssh_private_key:
        db_resource_dict["ssh_private_key_enc"] = encrypt_string(resource_data.ssh_private_key)
        
    db_resource = Resource(**db_resource_dict)
    
    if auto_discovery:
        db_resource.status = ResourceStatus.ACTIVE
    
    if resource_data.ssh_password or resource_data.ssh_private_key:
        logger.info(f"Validating SSH credentials for {resource_data.ip_address}")
        
        def validate_ssh():
            client = create_secure_client()
            try:
                connect_kwargs = {
                    "hostname": resource_data.ip_address,
                    "port": resource_data.ssh_port,
                    "username": resource_data.ssh_username,
                    "timeout": 10,
                    "look_for_keys": False,
                    "allow_agent": False
                }
                
                if resource_data.ssh_private_key:
                    from io import StringIO
                    pkey = paramiko.RSAKey.from_private_key(StringIO(resource_data.ssh_private_key))
                    connect_kwargs["pkey"] = pkey
                else:
                    connect_kwargs["password"] = resource_data.ssh_password
                
                client.connect(**connect_kwargs)
            except (paramiko.AuthenticationException, paramiko.SSHException) as e:
                raise BadRequestException(message=f"SSH Connection Failed: {str(e)}")
            finally:
                client.close()
        
        await run_in_threadpool(validate_ssh)

    db.add(db_resource)
    await db.commit()
    await db.refresh(db_resource)
    
    # 3. Deploy Agent (Async/Background ideally, but doing sync for simplicity now)
    if auto_discovery:
        try:
            logger.info(f"Auto-deploying agent to {db_resource.name}...")
            
            # Determine backend URL for Alloy (Prometheus/Loki push endpoints will be derived from this)
            backend_url = resource_data.backend_url or settings.EXTERNAL_API_URL
            
            success, logs = await run_in_threadpool(
                deploy_alloy_agent,
                credentials=credentials, # type: ignore
                resource_id=db_resource.id,
                backend_url=backend_url
            )
            
            if success:
                logger.info(f"Agent deployed successfully to {db_resource.name}")
            else:
                logger.warning(f"Agent deployment failed for {db_resource.name}. Logs: {logs}")
                # We don't rollback creation, just warn
        except Exception as e:
            logger.error(f"Error deploying agent: {e}", exc_info=True)
    
    return db_resource


@router.put("/{resource_id}", response_model=ResourceInDB)
async def update_resource(
    resource_id: int,
    resource_update: ResourceUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Update resource"""
    resource = await db.get(Resource, resource_id)
    if not resource:
        raise NotFoundException(message="Resource not found")
    
    # Update fields
    update_data = resource_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(resource, field, value)
    
    await db.commit()
    await db.refresh(resource)
    
    return resource


@router.delete("/{resource_id}", response_model=MessageResponse)
async def delete_resource(
    resource_id: int,
    delete_request: Optional[ResourceDeleteRequest] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Delete resource and optionally uninstall agent
    
    If delete_request is provided with SSH credentials, the agent will be uninstalled
    from the remote server before deleting the resource from the database.
    """
    if current_user.role not in ["admin", "operator"]:
        raise PermissionDeniedException(message="Not enough permissions")
    
    resource = await db.get(Resource, resource_id)
    if not resource:
        raise NotFoundException(message="Resource not found")
    
    # Try to uninstall agent if requested and credentials provided
    agent_uninstalled = False
    uninstall_error = None
    
    logger.info(f"收到删除请求: resource_id={resource_id}, payload={delete_request}")
    
    if delete_request and delete_request.uninstall_agent and resource.ip_address:
        logger.info(f"准备卸载 Agent: host={resource.ip_address}, user={delete_request.ssh_username}")
        logger.warning("Legacy agent uninstaller removed. Skipping uninstallation.")
    
    # Clear Prometheus metrics for this resource before deletion
    clear_metrics(
        resource_id=str(resource.id),
        resource_name=resource.name,
        ip_address=resource.ip_address or ""
    )
    
    await db.delete(resource)
    await db.commit()
    
    response = {
        "message": "资源已成功删除",
        "agent_uninstalled": agent_uninstalled
    }
    
    if uninstall_error:
        response["warning"] = f"资源已删除，但 Agent 卸载失败: {uninstall_error}"
    
    return response


def merge_metrics(cpu_results, mem_results, disk_results, net_in_results, net_out_results) -> List[dict]:
    merged_data = {}
    
    def process_result(result_list, key):
        if not result_list:
            return
        for result in result_list:
            for ts, val in result.get("values", []):
                ts_key = int(float(ts))
                if ts_key not in merged_data:
                    merged_data[ts_key] = {
                        "timestamp": datetime.fromtimestamp(ts_key).isoformat(),
                        "cpu_usage": 0.0,
                        "memory_usage": 0.0,
                        "disk_usage": 0.0,
                        "network_in": 0.0,
                        "network_out": 0.0
                    }
                merged_data[ts_key][key] = float(val)

    process_result(cpu_results, "cpu_usage")
    process_result(mem_results, "memory_usage")
    process_result(disk_results, "disk_usage")
    process_result(net_in_results, "network_in")
    process_result(net_out_results, "network_out")
    
    sorted_ts = sorted(merged_data.keys())
    return [merged_data[ts] for ts in sorted_ts]


@router.get("/{resource_id}/metrics/history", response_model=MetricResponse)
async def get_metrics_history(
    resource_id: int,
    hours: int = Query(24, ge=1, le=168),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db)
):
    resource = await db.get(Resource, resource_id)
    if not resource:
        raise NotFoundException(message="Resource not found")
    
    prom_client = PrometheusClient()
    
    end = datetime.now(timezone.utc).timestamp()
    start = end - (hours * 3600)
    if hours <= 6:
        step = "1m"
    elif hours <= 24:
        step = "5m"
    else:
        step = "15m"
        
    cpu_query = f'100 - (avg by (resource_id) (irate(node_cpu_seconds_total{{mode="idle", resource_id="{resource_id}"}}[5m])) * 100)'
    mem_query = f'(node_memory_MemTotal_bytes{{resource_id="{resource_id}"}} - node_memory_MemAvailable_bytes{{resource_id="{resource_id}"}}) / node_memory_MemTotal_bytes{{resource_id="{resource_id}"}} * 100'
    disk_query = f'100 - ((node_filesystem_avail_bytes{{resource_id="{resource_id}", mountpoint="/"}} * 100) / node_filesystem_size_bytes{{resource_id="{resource_id}", mountpoint="/"}})'
    net_in_query = f'sum by (resource_id) (irate(node_network_receive_bytes_total{{resource_id="{resource_id}", device!~"lo|docker.*|veth.*"}}[5m]))'
    net_out_query = f'sum by (resource_id) (irate(node_network_transmit_bytes_total{{resource_id="{resource_id}", device!~"lo|docker.*|veth.*"}}[5m]))'

    cpu_results, mem_results, disk_results, net_in_results, net_out_results = await asyncio.gather(
        prom_client.query_range(cpu_query, start, end, step),
        prom_client.query_range(mem_query, start, end, step),
        prom_client.query_range(disk_query, start, end, step),
        prom_client.query_range(net_in_query, start, end, step),
        prom_client.query_range(net_out_query, start, end, step)
    )
    
    metrics = merge_metrics(cpu_results, mem_results, disk_results, net_in_results, net_out_results)
    
    return {
        "resource_id": resource_id,
        "metrics": metrics,
        "processes": []
    }


@router.get("/{resource_id}/disk-partitions")
async def get_disk_partitions(
    resource_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Get latest disk partitions info for a resource"""
    resource = await db.get(Resource, resource_id)
    if not resource:
        raise NotFoundException(message="Resource not found")
    
    prom_client = PrometheusClient()
    
    # Query for availability, size, and percent
    # Filter out tempfs, loop devices etc.
    common_filter = f'resource_id="{resource_id}", fstype!~"tmpfs|overlay|iso9660|squashfs", mountpoint!~"/boot.*|/var/lib/docker.*|/run.*"'
    usage_query = f'100 - ((node_filesystem_avail_bytes{{{common_filter}}} * 100) / node_filesystem_size_bytes{{{common_filter}}})'
    size_query = f'node_filesystem_size_bytes{{{common_filter}}}'
    avail_query = f'node_filesystem_avail_bytes{{{common_filter}}}'
    
    usage_data, size_data, avail_data = await asyncio.gather(
        prom_client.query(usage_query),
        prom_client.query(size_query),
        prom_client.query(avail_query),
    )
    partitions = {}
    
    for item in usage_data:
        m = item.get("metric", {}).get("mountpoint")
        if not m: continue
        val = float(item.get("value", [0, "0"])[1])
        partitions[m] = {
            "mountpoint": m, 
            "percent": round(val, 1), 
            "device": item.get("metric", {}).get("device")
        }
        
    for item in size_data:
        m = item.get("metric", {}).get("mountpoint")
        if m in partitions:
            val = float(item.get("value", [0, "0"])[1])
            partitions[m]["total_gb"] = round(val / (1024**3), 2)
            
    for item in avail_data:
        m = item.get("metric", {}).get("mountpoint")
        if m in partitions:
            val = float(item.get("value", [0, "0"])[1])
            partitions[m]["avail_gb"] = round(val / (1024**3), 2)
            partitions[m]["used_gb"] = round(partitions[m].get("total_gb", 0) - partitions[m]["avail_gb"], 2)
            
    return list(partitions.values())


@router.get("/stats/summary", response_model=ResourceStats)
async def get_resource_stats(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Get resource statistics summary"""
    
    # Execute counts efficiently
    total_query = select(func.count()).select_from(Resource)
    active_query = select(func.count()).select_from(Resource).filter(Resource.status == ResourceStatus.ACTIVE)
    inactive_query = select(func.count()).select_from(Resource).filter(Resource.status == ResourceStatus.INACTIVE)
    
    total = (await db.execute(total_query)).scalar()
    active = (await db.execute(active_query)).scalar()
    inactive = (await db.execute(inactive_query)).scalar()
    
    by_type = {}
    for resource_type in ResourceType:
        type_count_query = select(func.count()).select_from(Resource).filter(Resource.type == resource_type)
        count = (await db.execute(type_count_query)).scalar()
        by_type[resource_type.value] = count
    
    return {
        "total": total or 0,
        "active": active or 0,
        "inactive": inactive or 0,
        "by_type": by_type
    }


@router.post("/probe", response_model=ResourceProbeResponse)
async def probe_resource(
    probe_request: ResourceProbeRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    Probe a remote server via SSH to auto-detect hardware specs
    Returns: CPU cores, memory, disk, OS info
    """
    try:
        credentials = CredentialService.build_ssh_credentials(
            ip_address=probe_request.ip_address,
            port=probe_request.ssh_port,
            username=probe_request.ssh_username,
            password=probe_request.ssh_password,
            private_key=probe_request.ssh_private_key
        )
        
        # Execute probe
        server_info = await run_in_threadpool(probe_server, credentials)
        
        return ResourceProbeResponse(
            hostname=server_info.hostname,
            cpu_cores=server_info.cpu_cores,
            memory_gb=server_info.memory_gb,
            disk_gb=server_info.disk_gb,
            os_type=server_info.os_type,
            os_version=server_info.os_version,
            kernel_version=server_info.kernel_version
        )
    except ConnectionError as e:
        raise InternalServerError(message=f"SSH连接失败: {str(e)}")
    except Exception as e:
        raise InternalServerError(message=f"探测失败: {str(e)}")


@router.post("/{resource_id}/deploy-alloy", response_model=TaskExecutionMessage)
async def deploy_alloy_monitoring_agent(
    resource_id: int,
    probe_request: ResourceProbeRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Deploy Grafana Alloy agent to remote server (Offline-ready)
    The agent will push metrics and logs to Prometheus and Loki
    """
    resource = await db.get(Resource, resource_id)
    if not resource:
        raise NotFoundException(message="Resource not found")
    
    try:
        backend_url = probe_request.backend_url or settings.EXTERNAL_API_URL
        
        task = Task(
            name=f"Deploy Alloy to {resource.ip_address}",
            description=f"Automated Alloy agent deployment for resource {resource.id}",
            task_type="deploy_alloy",
            target_resources=[resource_id],
            status=TaskStatus.PENDING,
            created_by=current_user.username
        )
        db.add(task)
        await db.commit()
        await db.refresh(task)
        
        deploy_alloy_task.delay(
            task.id, 
            resource_id, 
            backend_url,
            ssh_username=probe_request.ssh_username,
            ssh_password=probe_request.ssh_password,
            ssh_private_key=probe_request.ssh_private_key,
            ssh_port=probe_request.ssh_port
        )
        
        return {
            "task_id": task.id,
            "message": "Deployment started"
        }
    except Exception as e:
        logger.error(f"Failed to queue Alloy deployment for resource {resource_id}: {e}", exc_info=True)
        raise InternalServerError(message=f"部署启动失败: {str(e)}")
