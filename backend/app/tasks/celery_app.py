from celery import Celery
from app.core.config import settings


# Initialize Celery app
celery_app = Celery(
    "ops-platform",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=['app.tasks.monitoring', 'app.tasks.deployment', 'app.tasks.automation']
)


# Celery configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    beat_scheduler='redbeat.RedBeatScheduler',
    redbeat_redis_url=settings.REDIS_URL,
)

# Auto-discover tasks
celery_app.autodiscover_tasks(['app.tasks'])

# Configure periodic tasks
celery_app.conf.beat_schedule = {
    "sync-resource-status-every-15s": {
        "task": "sync_resource_status",
        "schedule": 15.0,
    },
}



@celery_app.task
def test_task():
    """Test task"""
    return "Task executed successfully"
