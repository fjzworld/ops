import paramiko
import logging

logger = logging.getLogger(__name__)

def create_secure_client() -> paramiko.SSHClient:
    """
    Create an SSH client configured for automated/containerized environments.
    
    Uses AutoAddPolicy because:
    - Celery workers run in Docker containers without pre-populated known_hosts
    - Target hosts are internal infrastructure managed by this platform
    - Strict RejectPolicy would reject ALL first-time connections
    
    Returns:
        paramiko.SSHClient: A configured SSH client instance.
    """
    client = paramiko.SSHClient()
    
    # Do NOT load system host keys in containerized environments.
    # load_system_host_keys() can cause "not found in known_hosts" errors
    # even when AutoAddPolicy is set, because system keys are checked first
    # with a stricter policy.

    # AutoAddPolicy: automatically add unknown host keys
    # Suitable for internal infrastructure managed by this platform
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    return client

