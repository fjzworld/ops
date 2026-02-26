import logging
from celery.schedules import crontab
from redbeat import RedBeatSchedulerEntry
from app.tasks.celery_app import celery_app
from app.models.operation import Operation

logger = logging.getLogger(__name__)

class SchedulerService:
    @staticmethod
    def validate_cron(schedule_str: str):
        """
        Validate cron string. Raises ValueError if invalid.
        """
        if not schedule_str:
            raise ValueError("Schedule string cannot be empty")
            
        try:
            parts = schedule_str.strip().split()
            if len(parts) != 5:
                raise ValueError("Invalid cron format: must have 5 parts (minute hour day_of_month month_of_year day_of_week)")
            
            # Use celery's crontab parser to validate values
            crontab(
                minute=parts[0],
                hour=parts[1],
                day_of_month=parts[2],
                month_of_year=parts[3],
                day_of_week=parts[4]
            )
        except Exception as e:
            raise ValueError(f"Invalid cron schedule '{schedule_str}': {str(e)}")

    @staticmethod
    def _parse_cron(schedule_str: str):
        """Parse cron string into celery crontab object"""
        if not schedule_str:
            return None
            
        # Handle standard 5-part cron
        parts = schedule_str.strip().split()
        if len(parts) != 5:
            # We preserve the logging here for backward compatibility if needed, 
            # but ideally callers should use validate_cron first.
            logger.warning(f"Invalid cron format (must have 5 parts): {schedule_str}")
            return None
            
        minute, hour, day_of_month, month_of_year, day_of_week = parts
        
        return crontab(
            minute=minute,
            hour=hour,
            day_of_month=day_of_month,
            month_of_year=month_of_year,
            day_of_week=day_of_week
        )

    @staticmethod
    def get_task_key(task_id: int) -> str:
        return f"task-{task_id}"

    @classmethod
    def sync_task(cls, task: Operation):
        """
        Sync task schedule to RedBeat.
        If task is disabled or has invalid schedule, ensure it's removed.
        If task is enabled and valid, create/update entry.
        Propagates RedisError if connection fails.
        """
        key = cls.get_task_key(task.id)
        
        # Always try to remove existing entry first to ensure clean state/updates
        # We catch KeyError here because it's fine if the task didn't exist in scheduler
        cls.delete_task(task.id)

        if not task.enabled:
            logger.info(f"Task {task.id} is disabled. Removed from scheduler.")
            return

        if not task.schedule:
            logger.info(f"Task {task.id} has no schedule. Removed from scheduler.")
            return

        schedule = cls._parse_cron(task.schedule)
        if not schedule:
            logger.warning(f"Task {task.id} has invalid schedule '{task.schedule}'. Not scheduling.")
            return

        # Propagate exceptions (like Redis connection errors)
        entry = RedBeatSchedulerEntry(
            name=key,
            task='app.tasks.automation.run_automation_task',
            schedule=schedule,
            args=[task.id],
            app=celery_app
        )
        entry.save()
        logger.info(f"Task {task.id} scheduled with cron '{task.schedule}'")

    @classmethod
    def delete_task(cls, task_id: int):
        """Remove task from RedBeat"""
        key = cls.get_task_key(task_id)
        try:
            entry = RedBeatSchedulerEntry(name=key, app=celery_app)
            entry.delete()
            logger.debug(f"Task {task_id} removed from scheduler")
        except KeyError:
            # Task not found in scheduler, which is fine
            pass
        # We do NOT catch other exceptions (like RedisError) so they propagate
