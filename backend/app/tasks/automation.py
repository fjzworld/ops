from app.tasks.celery_app import celery_app
from celery import chord, group
from app.core.database import SessionLocal
from app.models.operation import Operation, OperationStatus, OperationExecution, OperationType
from app.models.resource import Resource
from app.services.credential_service import CredentialService
from app.core.ssh import create_secure_client
from datetime import datetime, timezone
import logging
import io
import traceback
import socket
import paramiko

logger = logging.getLogger(__name__)

CONNECT_TIMEOUT = 15
EXEC_TIMEOUT = 300
MAX_OUTPUT_SIZE = 1 * 1024 * 1024  # 1MB

def _create_execution_history(db, operation: Operation, start_time: datetime):
    new_execution = OperationExecution(
        operation_id=operation.id,
        operation_type=OperationType.SCRIPT_EXEC,
        status=operation.status,
        start_time=start_time,
        end_time=datetime.now(timezone.utc),
        output=operation.last_output,
        error=operation.last_error
    )
    db.add(new_execution)
    return new_execution

def _execute_ssh_script(resource: Resource, script_content: str) -> dict:
    ssh = create_secure_client()
    # Explicitly set policy to handle containerized environments where known_hosts is missing
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    output_buffer = io.StringIO()
    exit_code = -1
    status = "failed"
    
    try:
        output_buffer.write(f"--- Resource: {resource.name} ({resource.ip_address}) ---\n")
        
        # Use CredentialService to get resource credentials
        credentials = CredentialService.get_ssh_credentials(resource)
        
        ssh.connect(
            hostname=credentials.host,
            port=credentials.port,
            username=credentials.username,
            password=credentials.password,
            pkey=paramiko.RSAKey.from_private_key(io.StringIO(credentials.private_key)) if credentials.private_key else None,
            timeout=CONNECT_TIMEOUT
        )

        stdin, stdout, stderr = ssh.exec_command(script_content, timeout=EXEC_TIMEOUT)
        
        out_content = stdout.read(MAX_OUTPUT_SIZE).decode('utf-8', errors='replace')
        err_content = stderr.read(MAX_OUTPUT_SIZE).decode('utf-8', errors='replace')
        
        exit_code = stdout.channel.recv_exit_status()
        
        output_buffer.write(f"STDOUT:\n{out_content}\n")
        if err_content:
            output_buffer.write(f"STDERR:\n{err_content}\n")
        
        output_buffer.write(f"Exit Code: {exit_code}\n")
        
        if exit_code == 0:
            status = "success"
        else:
            status = "failed"

    except paramiko.AuthenticationException:
        msg = f"Authentication failed for resource {resource.name}"
        logger.error(msg)
        output_buffer.write(f"Execution Error: {msg}\n")
    except paramiko.SSHException as e:
        msg = f"SSH error for resource {resource.name}: {str(e)}"
        logger.error(msg)
        output_buffer.write(f"Execution Error: {msg}\n")
    except socket.timeout:
        msg = f"Connection timed out for resource {resource.name}"
        logger.error(msg)
        output_buffer.write(f"Execution Error: {msg}\n")
    except Exception as e:
        msg = f"Failed to execute task on resource {resource.name}: {str(e)}"
        logger.error(msg)
        output_buffer.write(f"Execution Error: {msg}\n")
    finally:
        ssh.close()

    return {
        "resource_id": resource.id,
        "status": status,
        "output": output_buffer.getvalue(),
        "exit_code": exit_code
    }

@celery_app.task(bind=True)
def execute_single_resource(self, task_id: int, resource_id: int):
    """
    Execute automation script on a single resource.
    Returns execution result without updating Operation status in DB.
    """
    script_content = None
    resource = None
    task_found = False
    
    try:
        with SessionLocal() as db:
            operation = db.query(Operation).filter(Operation.id == task_id).first()
            if operation:
                task_found = True
                config = operation.config or {}
                script_content = config.get("script_content", "")
            
            resource_obj = db.query(Resource).filter(Resource.id == resource_id).first()
            if resource_obj:
                # Expunge object from session so we can use it after session closes
                db.expunge(resource_obj)
                resource = resource_obj
    except Exception as e:
        logger.error(f"Database error in execute_single_resource: {str(e)}")
        return {
            "resource_id": resource_id,
            "status": "failed",
            "output": f"Database error: {str(e)}",
            "exit_code": -1
        }

    if not task_found:
        return {
            "resource_id": resource_id,
            "status": "failed",
            "output": f"Operation {task_id} not found",
            "exit_code": -1
        }
    
    if resource is None:
        return {
            "resource_id": resource_id,
            "status": "failed",
            "output": f"Resource {resource_id} not found",
            "exit_code": -1
        }

    try:
        # Ensure script_content is a string
        safe_script_content = script_content if script_content is not None else ""
        return _execute_ssh_script(resource, safe_script_content)
    except Exception as e:
        logger.error(f"Critical error in execute_single_resource: {str(e)}")
        return {
            "resource_id": resource_id,
            "status": "failed",
            "output": f"Critical system error: {str(e)}",
            "exit_code": -1
        }

@celery_app.task(bind=True)
def summarize_automation_results(self, results, task_id: int):
    """
    Aggregate results from parallel execution and update Operation status.
    """
    logger.info(f"Summarizing results for operation {task_id}")
    try:
        with SessionLocal() as db:
            operation = db.query(Operation).filter(Operation.id == task_id).first()
            if not operation:
                logger.error(f"Operation {task_id} not found during summarization")
                return f"Error: Operation {task_id} not found"

            success_count = 0
            failure_count = 0
            overall_output = []

            # Results is a list of dicts from execute_single_resource
            for res in results:
                # Handle potential failures passed as exceptions if celery is configured to propagate them
                if isinstance(res, Exception):
                    overall_output.append(f"Task execution error: {str(res)}")
                    failure_count += 1
                    continue
                
                if not isinstance(res, dict):
                    overall_output.append(f"Invalid result format: {res}")
                    failure_count += 1
                    continue

                output = res.get("output", "")
                overall_output.append(output)
                
                if res.get("status") == "success":
                    success_count += 1
                else:
                    failure_count += 1
            
            operation.last_output = "\n".join(overall_output)
            
            if failure_count > 0:
                operation.status = OperationStatus.FAILED
                operation.last_error = f"Execution failed on {failure_count} resources"
            else:
                operation.status = OperationStatus.SUCCESS
                operation.last_error = None
                
            operation.success_count += success_count
            operation.failure_count += failure_count
            
            _create_execution_history(db, operation, operation.last_run_at)
            
            db.commit()
            return f"Operation {task_id} summary: {success_count} success, {failure_count} failed"
    except Exception as e:
        logger.error(f"Error in summarize_automation_results: {str(e)}")
        # Try to update operation status if possible
        try:
            with SessionLocal() as db:
                try:
                    operation = db.query(Operation).filter(Operation.id == task_id).first()
                    if operation:
                        operation.status = OperationStatus.FAILED
                        operation.last_error = f"Summarization error: {str(e)}"
                        
                        _create_execution_history(db, operation, operation.last_run_at)
                        db.commit()
                except Exception:
                    db.rollback()
        except:
            pass
        raise e

@celery_app.task(bind=True)
def run_automation_task(self, task_id: int):
    """
    Dispatcher task: Spawns parallel executions for each target resource.
    """
    logger.info(f"Dispatching operation {task_id}")
    try:
        with SessionLocal() as db:
            operation = db.query(Operation).filter(Operation.id == task_id).first()
            if not operation:
                logger.error(f"Operation {task_id} not found")
                return f"Error: Operation {task_id} not found"
                
            # Update status to RUNNING
            operation.status = OperationStatus.RUNNING
            operation.last_run_at = datetime.now(timezone.utc)
            operation.execution_count += 1
            db.commit()
            
            target_resource_ids = operation.target_resources or []
            
            if not target_resource_ids:
                logger.warning(f"Operation {task_id} has no target resources")
                operation.status = OperationStatus.FAILED
                operation.last_output = "No target resources specified."
                operation.last_error = "No target resources"
                operation.failure_count += 1
                
                _create_execution_history(db, operation, operation.last_run_at)
                
                db.commit()
                return "No target resources"

            logger.info(f"Operation {task_id} targeting resources: {target_resource_ids}")

            # Create chord
            # header: group of tasks to execute in parallel
            header = group(execute_single_resource.s(task_id, res_id) for res_id in target_resource_ids)
            
            # callback: task to execute after all header tasks complete
            callback = summarize_automation_results.s(task_id)
            
            # Execute the chord
            chord(header)(callback)
            
            return f"Dispatched {len(target_resource_ids)} tasks for Operation {task_id}"
            
    except Exception as e:
        logger.error(f"Error dispatching operation {task_id}: {str(e)}")
        try:
            with SessionLocal() as db:
                try:
                    operation = db.query(Operation).filter(Operation.id == task_id).first()
                    if operation:
                        operation.status = OperationStatus.FAILED
                        operation.last_error = f"Dispatch error: {str(e)}"
                        _create_execution_history(db, operation, operation.last_run_at or datetime.now(timezone.utc))
                        db.commit()
                except Exception:
                    db.rollback()
        except Exception:
            pass
        raise e
