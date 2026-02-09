import paramiko
import logging

logger = logging.getLogger(__name__)

def create_secure_client() -> paramiko.SSHClient:
    """
    Create a secure SSH client with RejectPolicy and system host keys loaded.
    
    Returns:
        paramiko.SSHClient: A configured SSH client instance.
    """
    client = paramiko.SSHClient()
    
    # Load system host keys (e.g. from ~/.ssh/known_hosts)
    # This ensures we trust hosts that the system trusts.
    try:
        client.load_system_host_keys()
    except IOError:
        # It's possible the file doesn't exist or is not readable.
        # Log a warning but proceed, as we might rely on manually added keys later (though not in this scope)
        # or strict rejection.
        logger.warning("Could not load system host keys.")

    # Set policy to RejectPolicy to prevent MITM attacks
    # This rejects any host key that is not in the known_hosts file (or system host keys)
    client.set_missing_host_key_policy(paramiko.RejectPolicy())
    
    return client
