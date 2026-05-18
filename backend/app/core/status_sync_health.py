import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict

from app.core.rate_limit import redis_client

logger = logging.getLogger(__name__)

STATUS_SYNC_HEALTH_KEY = "ops:monitoring:status_sync_health"
STATUS_SYNC_HEALTH_TTL_SECONDS = 7 * 24 * 60 * 60


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_status_sync_health() -> Dict[str, Any]:
    raw = redis_client.get(STATUS_SYNC_HEALTH_KEY)
    if not raw:
        return {
            "status": "unknown",
            "last_run_at": None,
            "last_success_at": None,
            "active_count": 0,
            "offline_count": 0,
            "consecutive_zero_active_runs": 0,
            "last_error": None,
            "message": "状态同步任务尚未上报健康信息",
        }

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Failed to decode status sync health payload from Redis")
        return {
            "status": "unknown",
            "last_run_at": None,
            "last_success_at": None,
            "active_count": 0,
            "offline_count": 0,
            "consecutive_zero_active_runs": 0,
            "last_error": "invalid_health_payload",
            "message": "状态同步健康信息已损坏",
        }


def write_status_sync_health(updates: Dict[str, Any]) -> Dict[str, Any]:
    current = read_status_sync_health()
    payload = {**current, **updates}
    payload["updated_at"] = _utc_now_iso()
    redis_client.setex(
        STATUS_SYNC_HEALTH_KEY,
        STATUS_SYNC_HEALTH_TTL_SECONDS,
        json.dumps(payload, ensure_ascii=True),
    )
    return payload
