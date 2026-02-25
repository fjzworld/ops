import logging
from fastapi import APIRouter, Depends, Query, status
from fastapi.concurrency import run_in_threadpool
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
    MiddlewareCreate, MiddlewareUpdate, MiddlewareInDB, MiddlewareAction, 
    MiddlewareVerify, MiddlewareVerifyResult
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
    """Create a new middleware with auto status detection"""
    try:
        # Check if middleware name already exists under the same resource
        existing = await db.execute(
            select(Middleware).where(
                Middleware.name == middleware_data.name,
                Middleware.resource_id == middleware_data.resource_id
            )
        )
        if existing.scalars().first():
            raise BadRequestException(message="该资源下已存在同名中间件")

        db_middleware_dict = middleware_data.dict(exclude={"password_plain"})

        if middleware_data.password_plain:
            db_middleware_dict["password_enc"] = encrypt_string(middleware_data.password_plain)

        # Get resource info to detect actual status
        resource = await db.get(Resource, middleware_data.resource_id)
        initial_status = "unknown"
        
        if resource:
            try:
                creds = CredentialService.get_ssh_credentials(resource)
                detector = ResourceDetector(creds)
                
                # Quick status detection
                verify_result = await run_in_threadpool(
                    detector.verify_middleware,
                    mw_type=middleware_data.type,
                    port=middleware_data.port,
                    service_name=middleware_data.service_name,
                    username=middleware_data.username,
                    password=middleware_data.password_plain
                )
                
                # Set status based on verification result
                if verify_result.get("success"):
                    initial_status = "active"
                elif verify_result.get("port_reachable"):
                    initial_status = "error"  # Port open but auth failed
                else:
                    initial_status = "inactive"
                    
            except Exception as e:
                logger.warning(f"Failed to detect middleware status: {e}")
                initial_status = "unknown"
        
        db_middleware_dict["status"] = initial_status
        
        db_middleware = Middleware(**db_middleware_dict)
        db.add(db_middleware)
        await db.commit()
        
        # Fetch the created middleware with associated resource
        result = await db.execute(
            select(Middleware)
            .filter(Middleware.id == db_middleware.id)
            .options(selectinload(Middleware.resource))
        )
        return result.scalars().first()
    except Exception as e:
        logger.error(f"Error creating middleware: {str(e)}", exc_info=True)
        if isinstance(e, BadRequestException):
            raise
        raise InternalServerError(message=f"Failed to create middleware: {str(e)}")


@router.post("/verify", response_model=MiddlewareVerifyResult)
async def verify_middleware_config(
    verify_data: MiddlewareVerify,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    验证中间件配置是否正确
    在添加中间件前调用此接口进行验证
    返回细粒度的验证结果，包括 SSH 连接、端口、服务状态、认证和日志路径探测
    """
    # 获取资源信息
    resource = await db.get(Resource, verify_data.resource_id)
    if not resource:
        raise NotFoundException(message="资源不存在")

    try:
        # 获取SSH凭据
        creds = CredentialService.get_ssh_credentials(resource)

        # 执行验证
        detector = ResourceDetector(creds)
        result = await run_in_threadpool(
            detector.verify_middleware,
            mw_type=verify_data.type,
            port=verify_data.port,
            service_name=verify_data.service_name,
            username=verify_data.username,
            password=verify_data.password_plain
        )

        # 执行日志路径探测
        log_result = await run_in_threadpool(
            detector.detect_log_path,
            mw_type=verify_data.type,
            service_name=verify_data.service_name
        )

        # 合并日志路径探测结果
        result["log_path_found"] = log_result.get("found", False)
        result["suggested_log_path"] = log_result.get("path")
        if log_result.get("candidates"):
            result["details"]["log_candidates"] = log_result["candidates"]

        # 提取自动检测到的服务名称
        if result.get("details", {}).get("detected_service_name"):
            result["suggested_service_name"] = result["details"]["detected_service_name"]

        # 提取认证错误信息
        if not result.get("auth_valid") and result.get("details", {}).get("auth_test"):
            auth_test = result["details"]["auth_test"]
            if isinstance(auth_test, dict) and auth_test.get("error"):
                result["auth_message"] = auth_test["error"]

        # 标记 SSH 连接成功
        result["ssh_ok"] = True

        return result

    except BadRequestException as e:
        # SSH凭据问题
        return MiddlewareVerifyResult(
            success=False,
            ssh_ok=False,
            port_reachable=False,
            service_active=False,
            auth_valid=False,
            message=str(e.message),
            details={"error_type": "credential_error"}
        )
    except Exception as e:
        logger.error(f"Middleware verification failed: {e}")
        return MiddlewareVerifyResult(
            success=False,
            ssh_ok=False,
            port_reachable=False,
            service_active=False,
            auth_valid=False,
            message=f"验证失败: {str(e)}",
            details={"error_type": "unknown_error", "error": str(e)}
        )

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
    
    # Fetch the updated middleware with associated resource to avoid MissingGreenlet
    result = await db.execute(
        select(Middleware)
        .filter(Middleware.id == id)
        .options(selectinload(Middleware.resource))
    )
    return result.scalars().first()

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
    """Control middleware (start/stop/restart) via SSH"""
    middleware = await db.get(Middleware, id)
    if not middleware:
        raise NotFoundException(message="Middleware not found")
    
    # 检查是否有服务名称
    if not middleware.service_name:
        raise BadRequestException(message="未配置服务名称，无法执行服务操作")
    
    # 获取关联的资源
    resource = await db.get(Resource, middleware.resource_id)
    if not resource:
        raise NotFoundException(message="关联的资源不存在")
    
    action = action_data.action
    logger.info(f"Executing {action} on service {middleware.service_name} for resource {middleware.resource_id}")
    
    try:
        # 获取SSH凭据
        creds = CredentialService.get_ssh_credentials(resource)
        detector = ResourceDetector(creds)
        
        # 执行服务控制命令
        result = await run_in_threadpool(
            detector.control_service,
            service_name=middleware.service_name,
            action=action
        )
        
        # 更新状态
        if result.get("success"):
            if action in ["start", "restart"]:
                middleware.status = "active"
            elif action == "stop":
                middleware.status = "stopped"
            await db.commit()
            await db.refresh(middleware)
        
        return {
            "message": result.get("message", f"Service {action} executed"),
            "status": middleware.status,
            "output": result.get("output", "")
        }
        
    except BadRequestException as e:
        raise BadRequestException(message=str(e.message))
    except Exception as e:
        logger.error(f"Failed to control service: {e}")
        raise InternalServerError(message=f"服务操作失败: {str(e)}")

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
