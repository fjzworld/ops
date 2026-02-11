import logging
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from typing import List, Optional
from app.core.database import get_async_db
from app.models.user import User
from app.models.middleware import Middleware
from app.models.resource import Resource
from app.services.credential_service import CredentialService
from app.services.resource_detector import ResourceDetector, SSHCredentials
from app.schemas.middleware import (
    MiddlewareCreate, MiddlewareUpdate, MiddlewareInDB, MiddlewareAction
)
from app.api.v1.auth import get_current_active_user
from app.core.encryption import encrypt_string, decrypt_string
from app.core.exceptions import NotFoundException, BadRequestException, InternalServerError

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/", response_model=List[MiddlewareInDB])
async def list_middlewares(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=1000),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db)
):
    """List all middlewares"""
    result = await db.execute(
        select(Middleware)
        .options(selectinload(Middleware.resource))
        .offset(skip).limit(limit)
    )
    middlewares = result.scalars().all()
    return middlewares

@router.post("/", response_model=MiddlewareInDB, status_code=status.HTTP_201_CREATED)
async def create_middleware(
    middleware_data: MiddlewareCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Create a new middleware"""
    # Check if middleware name already exists (optional but good practice)
    existing = await db.execute(select(Middleware).filter(Middleware.name == middleware_data.name))
    if existing.scalars().first():
        raise BadRequestException(message="Middleware with this name already exists")

    db_middleware_dict = middleware_data.dict(exclude={"password_plain"})
    
    if middleware_data.password_plain:
        db_middleware_dict["password_enc"] = encrypt_string(middleware_data.password_plain)
    
    db_middleware = Middleware(**db_middleware_dict)
    db.add(db_middleware)
    await db.commit()
    await db.refresh(db_middleware)
    return db_middleware

@router.get("/{id}", response_model=MiddlewareInDB)
async def get_middleware(
    id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Get middleware by ID"""
    result = await db.execute(
        select(Middleware)
        .filter(Middleware.id == id)
        .options(selectinload(Middleware.resource))
    )
    middleware = result.scalars().first()
    if not middleware:
        raise NotFoundException(message="Middleware not found")
    return middleware

@router.put("/{id}", response_model=MiddlewareInDB)
async def update_middleware(
    id: int,
    middleware_update: MiddlewareUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Update middleware"""
    middleware = await db.get(Middleware, id)
    if not middleware:
        raise NotFoundException(message="Middleware not found")
    
    update_data = middleware_update.dict(exclude_unset=True)
    
    # Handle password encryption if changed
    if "password_plain" in update_data:
        password_plain = update_data.pop("password_plain")
        if password_plain:
            update_data["password_enc"] = encrypt_string(password_plain)
    
    for field, value in update_data.items():
        setattr(middleware, field, value)
    
    await db.commit()
    await db.refresh(middleware)
    return middleware

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_middleware(
    id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Delete middleware"""
    middleware = await db.get(Middleware, id)
    if not middleware:
        raise NotFoundException(message="Middleware not found")
    
    await db.delete(middleware)
    await db.commit()
    return None

@router.post("/{id}/action", status_code=status.HTTP_200_OK)
async def control_middleware(
    id: int,
    action_data: MiddlewareAction,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Control middleware (start/stop/restart)"""
    middleware = await db.get(Middleware, id)
    if not middleware:
        raise NotFoundException(message="Middleware not found")
    
    action = action_data.action
    logger.info(f"Mocking {action} service {middleware.service_name} on resource {middleware.resource_id}")
    
    if action in ["start", "restart"]:
        middleware.status = "active"
    elif action == "stop":
        middleware.status = "stopped"
        
    await db.commit()
    await db.refresh(middleware)
    
    return {"message": f"Service {action} signal sent successfully", "status": middleware.status}

@router.get("/{id}/metrics")
async def get_middleware_metrics(
    id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Get middleware metrics with auto status detection"""
    middleware = await db.get(Middleware, id)
    
    if not middleware:
        raise NotFoundException(message="Middleware not found")
    
    resource = await db.get(Resource, middleware.resource_id)
    if not resource:
        raise NotFoundException(message="Associated resource not found")
    
    try:
        # Use CredentialService to get resource credentials
        creds = CredentialService.get_ssh_credentials(resource)
        
        # Optimized: Check status and collect metrics in one SSH session
        detector = ResourceDetector(creds)
        mw_password = decrypt_string(middleware.password_enc) if middleware.password_enc else None
        
        from fastapi.concurrency import run_in_threadpool
        metrics = await run_in_threadpool(
            detector.get_metrics_and_status,
            mw_type=middleware.type,
            port=middleware.port,
            service_name=middleware.service_name,
            username=middleware.username,
            password=mw_password
        )
        
        # Update status if changed
        new_status = metrics.get("status", "unknown")
        if new_status != middleware.status and new_status != "unknown":
            middleware.status = new_status
            await db.commit()
            logger.info(f"Updated middleware {middleware.name} status to: {new_status}")
            
        return metrics
        
    except Exception as e:
        logger.error(f"Failed to collect metrics: {e}")
        raise InternalServerError(message=f"Failed to collect metrics: {str(e)}")

import asyncio
from concurrent.futures import ThreadPoolExecutor
from fastapi import WebSocket, WebSocketDisconnect

@router.websocket("/{id}/log-stream")
async def log_stream_endpoint(
    websocket: WebSocket,
    id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """Real-time log stream via WebSocket"""
    await websocket.accept()
    
    middleware = await db.get(Middleware, id)
    if not middleware or not middleware.log_path:
        await websocket.send_text("Middleware not found or log path not configured")
        await websocket.close()
        return

    resource = await db.get(Resource, middleware.resource_id)
    if not resource:
        await websocket.send_text("Resource not found")
        await websocket.close()
        return

    try:
        # Use CredentialService to get resource credentials
        creds = CredentialService.get_ssh_credentials(resource)
        
        detector = ResourceDetector(creds)
        logger.info(f"Connecting to {resource.ip_address} for logs...")
        
        # Run blocking connect in executor
        loop = asyncio.get_event_loop()
        try:
            await loop.run_in_executor(None, detector.connect)
            logger.info("SSH connection established.")
        except Exception as e:
             logger.error(f"SSH Connect failed: {e}")
             await websocket.send_text(f"[System Error] 无法连接服务器: {str(e)}")
             await websocket.close()
             return

        # Use shell check to ensure clear error if file missing
        cmd = f"if [ -f '{middleware.log_path}' ]; then tail -n 100 -f '{middleware.log_path}'; else echo 'Error: Log file not found at {middleware.log_path}'; exit 1; fi"
        logger.info(f"Executing command: {cmd}")
        
        # blocking exec_command
        stdin, stdout, stderr = await loop.run_in_executor(None, lambda: detector.client.exec_command(cmd, get_pty=False))
        
        try:
            while True:
                # blocking readline
                line = await loop.run_in_executor(None, stdout.readline)
                if not line:
                    # EOF reached. Check stderr for errors
                    err = await loop.run_in_executor(None, lambda: stderr.read().decode())
                    if err:
                        await websocket.send_text(f"System Error: {err}")
                    elif stdout.channel.exit_status_ready() and stdout.channel.recv_exit_status() != 0:
                         await websocket.send_text("Log stream ended unexpectedly.")
                    else:
                         # Just EOF
                         pass
                    break
                await websocket.send_text(line)
        except WebSocketDisconnect:
            logger.info("WebSocket disconnected")
        except Exception as e:
            logger.error(f"Log stream error: {e}")
            await websocket.send_text(f"Error reading logs: {str(e)}")
        finally:
            logger.info("Closing SSH connection for logs")
            # blocking close
            await loop.run_in_executor(None, detector.close)
            
    except Exception as e:
        logger.error(f"Log stream connection failed: {e}")
        try:
            await websocket.send_text(f"[System Error] 无法建立连接: {str(e)}")
            await websocket.close()
        except:
            pass
