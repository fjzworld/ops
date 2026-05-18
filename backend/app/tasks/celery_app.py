import logging
import os

from celery import Celery
from celery.signals import beat_init
from app.core.config import settings

logger = logging.getLogger(__name__)

DEFAULT_BEAT_SCHEDULER = "redbeat.RedBeatScheduler"
SYNC_RESOURCE_STATUS_TASK = "sync_resource_status"
SYNC_RESOURCE_STATUS_ENTRY = "system:sync-resource-status-every-15s"
SYNC_RESOURCE_STATUS_INTERVAL_SECONDS = 15.0
beat_scheduler = os.getenv("CELERY_BEAT_SCHEDULER", DEFAULT_BEAT_SCHEDULER)

# Initialize Celery app
celery_app = Celery(
    "ops-platform",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.monitoring", "app.tasks.deployment", "app.tasks.automation"],
)


# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    beat_scheduler=beat_scheduler,
)

if beat_scheduler == DEFAULT_BEAT_SCHEDULER:
    celery_app.conf.update(redbeat_redis_url=settings.REDIS_URL)

# Auto-discover tasks
celery_app.autodiscover_tasks(["app.tasks"])

# Configure periodic tasks
if beat_scheduler == DEFAULT_BEAT_SCHEDULER:

    @beat_init.connect
    def ensure_system_periodic_tasks(sender=None, **kwargs):
        try:
            from redbeat import RedBeatSchedulerEntry

            entry = RedBeatSchedulerEntry(
                name=SYNC_RESOURCE_STATUS_ENTRY,
                task=SYNC_RESOURCE_STATUS_TASK,
                schedule=SYNC_RESOURCE_STATUS_INTERVAL_SECONDS,
                app=celery_app,
            )
            entry.save()
            logger.info(
                "Ensured RedBeat periodic task '%s' every %ss",
                SYNC_RESOURCE_STATUS_TASK,
                SYNC_RESOURCE_STATUS_INTERVAL_SECONDS,
            )
        except Exception as exc:
            logger.error(
                "Failed to ensure RedBeat periodic task '%s': %s",
                SYNC_RESOURCE_STATUS_TASK,
                exc,
            )
else:
    celery_app.conf.beat_schedule = {
        "sync-resource-status-every-15s": {
            "task": SYNC_RESOURCE_STATUS_TASK,
            "schedule": SYNC_RESOURCE_STATUS_INTERVAL_SECONDS,
        },
    }


@celery_app.task
def test_task():
    """Test task"""
    return "Task executed successfully"
