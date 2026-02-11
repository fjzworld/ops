from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app
from sqlalchemy import select
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.core.config import settings
from app.core.database import engine, Base, AsyncSessionLocal, async_engine
from app.core.exceptions import AppException
from app.core.rate_limit import limiter
from app.api.v1 import auth, users, resources, monitoring, alerts, automation, containers, middlewares, logs
from app.services.scheduler import SchedulerService
from app.models.task import Task

import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events"""
    # Create database tables
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Sync tasks to RedBeat on startup
    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(select(Task))
            tasks = result.scalars().all()
            for task in tasks:
                SchedulerService.sync_task(task)
            print(f"Synced {len(tasks)} tasks to scheduler")
        except Exception as e:
            print(f"Error syncing tasks on startup: {e}")
    
    yield

# Initialize FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Operations Platform API",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan
)

# Add rate limiter to app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])
# NOTE: containers router must be registered BEFORE resources router
# to avoid route conflict with /{id} catching /1/containers
app.include_router(containers.router, prefix="/api/v1/resources", tags=["Containers"])
app.include_router(resources.router, prefix="/api/v1/resources", tags=["Resources"])
app.include_router(monitoring.router, prefix="/api/v1/monitoring", tags=["Monitoring"])
app.include_router(alerts.router, prefix="/api/v1/alerts", tags=["Alerts"])
app.include_router(automation.router, prefix="/api/v1/automation", tags=["Automation"])
app.include_router(middlewares.router, prefix="/api/v1/middlewares", tags=["Middlewares"])
app.include_router(logs.router, prefix="/api/v1/logs", tags=["Logs"])

# Prometheus metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    """Handle application exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.status_code,
            "message": exc.message,
            "details": exc.details
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors"""
    return JSONResponse(
        status_code=422,
        content={
            "code": 422,
            "message": "Validation Error",
            "details": exc.errors()
        }
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler - 生产环境不暴露详细错误信息"""
    import traceback
    
    # 记录详细错误日志（用于调试）
    error_trace = traceback.format_exc()
    print(f"[ERROR] {request.method} {request.url}: {str(exc)}\n{error_trace}")
    
    # 生产环境返回通用错误，开发环境返回详细信息
    if settings.DEBUG:
        return JSONResponse(
            status_code=500,
            content={
                "code": 500,
                "message": f"Internal server error: {str(exc)}",
                "details": {"trace": error_trace}
            }
        )
    else:
        return JSONResponse(
            status_code=500,
            content={
                "code": 500,
                "message": "Internal server error",
                "details": {}
            }
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
