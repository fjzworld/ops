import logging
from datetime import datetime
from app.tasks.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.task import Task, TaskStatus
from app.models.resource import Resource
from app.services.alloy_deployer import deploy_alloy_agent
from app.services.resource_detector import SSHCredentials

from app.services.credential_service import CredentialService

logger = logging.getLogger(__name__)

@celery_app.task(name="app.tasks.deployment.deploy_alloy_task")
def deploy_alloy_task(
    task_id: int, 
    resource_id: int, 
    backend_url: str,
    ssh_username: str = None,
    ssh_password: str = None,
    ssh_private_key: str = None,
    ssh_port: int = None
):
    logger.info(f"DEBUG: Entering deploy_alloy_task for task {task_id}")
    db = SessionLocal()
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            logger.error(f"Task {task_id} not found")
            return

        resource = db.query(Resource).get(resource_id)
        if not resource:
            error_msg = f"Resource {resource_id} not found"
            task.status = TaskStatus.FAILED
            task.last_error = error_msg
            db.commit()
            return
            
        # Create execution record
        from app.models.task import TaskExecution
        execution = TaskExecution(
            task_id=task.id,
            status=TaskStatus.RUNNING,
            start_time=datetime.now()
        )
        db.add(execution)
        db.commit()
        db.refresh(execution)

        task.last_run_at = datetime.now()
        db.commit()

        # Fix: Only use provided credentials if a password or key is actually provided.
        # Just having a username (which might be default) is not enough to define new credentials.
        if ssh_password or ssh_private_key:
            credentials = SSHCredentials(
                host=resource.ip_address,
                port=ssh_port or resource.ssh_port or 22,
                username=ssh_username or resource.ssh_username or "root",
                password=ssh_password,
                private_key=ssh_private_key
            )
        else:
            try:
                # If no password/key provided in request, try to load from DB (encrypted)
                credentials = CredentialService.get_ssh_credentials(resource)
            except Exception as e:
                error_msg = f"Failed to load credentials: {str(e)}"
                task.status = TaskStatus.FAILED
                task.last_error = error_msg
                
                execution.status = TaskStatus.FAILED
                execution.end_time = datetime.now()
                execution.error = error_msg
                db.commit()
                return

        try:
            success, logs = deploy_alloy_agent(
                credentials=credentials,
                resource_id=resource.id,
                backend_url=backend_url
            )

            execution.end_time = datetime.now()
            execution.output = logs
            
            if success:
                task.status = TaskStatus.SUCCESS
                task.last_output = logs
                task.success_count += 1
                
                execution.status = TaskStatus.SUCCESS
            else:
                task.status = TaskStatus.FAILED
                task.last_error = "Deployment failed. Check execution logs."
                task.last_output = logs
                task.failure_count += 1
                
                execution.status = TaskStatus.FAILED
                execution.error = "Deployment failed"
                
        except Exception as e:
            logger.exception(f"Error during Alloy deployment: {e}")
            error_msg = str(e)
            
            task.status = TaskStatus.FAILED
            task.last_error = error_msg
            task.failure_count += 1
            
            execution.status = TaskStatus.FAILED
            execution.end_time = datetime.now()
            execution.error = error_msg

        task.execution_count += 1
        db.commit()

    finally:
        db.close()
