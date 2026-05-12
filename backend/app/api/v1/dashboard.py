from fastapi import APIRouter, Depends, Query
from fastapi.concurrency import run_in_threadpool
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_active_user
from app.core.database import get_async_db
from app.core.exceptions import BadRequestException
from app.models.user import User
from app.schemas.algorithm_dashboard import (
    AlgorithmDashboardConfigRead,
    AlgorithmDashboardConfigTestRequest,
    AlgorithmDashboardConfigTestResult,
    AlgorithmDashboardConfigUpdate,
    AlgorithmDashboardMonthsResponse,
    AlgorithmRuntimeDashboardResponse,
    AlgorithmRuntimeQuery,
)
from app.services.algorithm_dashboard import (
    AlgorithmDashboardConfigService,
    AlgorithmDashboardService,
)

router = APIRouter()


@router.get(
    "/algorithm-runtime/config",
    response_model=AlgorithmDashboardConfigRead,
)
async def get_algorithm_runtime_config(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
):
    return await AlgorithmDashboardConfigService.get_config_async(db)


@router.put(
    "/algorithm-runtime/config",
    response_model=AlgorithmDashboardConfigRead,
)
async def update_algorithm_runtime_config(
    payload: AlgorithmDashboardConfigUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
):
    return await AlgorithmDashboardConfigService.upsert_config_async(db, payload)


@router.post(
    "/algorithm-runtime/config/test",
    response_model=AlgorithmDashboardConfigTestResult,
)
async def test_algorithm_runtime_config(
    payload: AlgorithmDashboardConfigTestRequest,
    current_user: User = Depends(get_current_active_user),
):
    return await run_in_threadpool(AlgorithmDashboardConfigService.test_connection, payload)


@router.get(
    "/algorithm-runtime/months",
    response_model=AlgorithmDashboardMonthsResponse,
)
async def list_algorithm_runtime_months(
    current_user: User = Depends(get_current_active_user),
):
    return await run_in_threadpool(AlgorithmDashboardService.list_months)


@router.get(
    "/algorithm-runtime",
    response_model=AlgorithmRuntimeDashboardResponse,
)
async def get_algorithm_runtime_dashboard(
    month: str = Query(..., pattern=r"^\d{6}$"),
    from_time: str = Query("now-3h", alias="from"),
    to_time: str = Query("now", alias="to"),
    timezone: str = Query("Asia/Shanghai"),
    current_user: User = Depends(get_current_active_user),
):
    try:
        query = AlgorithmRuntimeQuery(
            month=month,
            from_time=from_time,
            to_time=to_time,
            timezone=timezone,
        )
        query.resolve_window()
    except (ValidationError, ValueError) as exc:
        raise BadRequestException(message="算法看板查询参数无效") from exc

    return await run_in_threadpool(
        AlgorithmDashboardService.fetch_algorithm_runtime,
        query,
    )
