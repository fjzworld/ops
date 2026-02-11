import logging
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_async_db
from app.models.user import User
from app.models.resource import Resource
from app.api.v1.auth import get_current_active_user
from app.services.monitoring_service import MonitoringService
from app.core.exceptions import InternalServerError
import httpx
import os
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)
router = APIRouter()

PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://prometheus:9090")

# --- Prometheus Proxy Endpoints ---

@router.get("/query")
async def query_prometheus(
    query: str,
    time: float = None,
    current_user: User = Depends(get_current_active_user)
):
    """
    Proxy query to Prometheus (Instant Query)
    Example: query=opspro_cpu_usage_percent
    """
    params = {"query": query}
    if time:
        params["time"] = str(time)
        
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{PROMETHEUS_URL}/api/v1/query", params=params)
            return resp.json()
        except httpx.RequestError as e:
            raise InternalServerError(message=f"Prometheus connection failed: {e}")

@router.get("/query_range")
async def query_range_prometheus(
    query: str,
    start: float,
    end: float,
    step: int = 60,
    current_user: User = Depends(get_current_active_user)
):
    """
    Proxy query to Prometheus (Range Query)
    Returns simplified format: [{time: timestamp, value: value}, ...]
    """
    params = {
        "query": query,
        "start": str(start),
        "end": str(end),
        "step": str(step)
    }
        
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{PROMETHEUS_URL}/api/v1/query_range", params=params)
            prom_data = resp.json()
            
            # Transform Prometheus format to simplified format for frontend
            if prom_data.get("status") == "success":
                result = prom_data.get("data", {}).get("result", [])
                if result and len(result) > 0:
                    # Get values from first result (assuming single series query)
                    values = result[0].get("values", [])
                    # Transform [[timestamp, "value"], ...] to [{time: ts, value: val}, ...]
                    transformed = [{"time": v[0], "value": v[1]} for v in values]
                    return transformed
            
            return []
        except httpx.RequestError as e:
            raise InternalServerError(message=f"Prometheus connection failed: {e}")

# --- Existing Dashboard Endpoint (Legacy/Hybrid) ---

@router.get("/dashboard")
async def get_dashboard_data(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Get dashboard monitoring data
    """
    return await MonitoringService.get_dashboard_stats(db)
