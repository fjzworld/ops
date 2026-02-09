"""Initialize tasks package"""
from app.tasks.celery_app import celery_app
from app.tasks.automation import run_automation_task

__all__ = ["celery_app", "run_automation_task"]
