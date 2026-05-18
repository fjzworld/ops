import os
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

    # 生产环境强制主机密钥验证
    if os.getenv("SSH_VERIFY_HOST_KEYS", "").lower() == "true":
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.RejectPolicy())
    else:
        logger.warning(
            "SSH AutoAddPolicy enabled — host keys are NOT verified. "
            "Set SSH_VERIFY_HOST_KEYS=true in production."
        )
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    return client
