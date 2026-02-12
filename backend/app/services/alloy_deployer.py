import os
from pathlib import Path
import logging
import paramiko
from jinja2 import Environment, FileSystemLoader
from app.services.resource_detector import SSHCredentials
from app.core.ssh import create_secure_client
from app.core.config import settings

logger = logging.getLogger(__name__)

from typing import Tuple, Optional

def deploy_alloy_agent(
    credentials: SSHCredentials,
    resource_id: int,
    backend_url: str,
    prometheus_url: Optional[str] = None,
    loki_url: Optional[str] = None
) -> Tuple[bool, str]:
    """
    Deploy Grafana Alloy agent to a remote resource with offline support.
    Returns: (success, logs)
    """
    
    logs = []
    def log(msg):
        logger.info(msg)
        logs.append(msg)

    client = create_secure_client()
    
    try:
        log(f"Starting Alloy deployment for {credentials.host}...")
        
        if credentials.private_key:
            key = paramiko.RSAKey.from_private_key_file(credentials.private_key)
            client.connect(
                hostname=credentials.host,
                port=credentials.port,
                username=credentials.username,
                pkey=key,
                timeout=15,
                look_for_keys=False,
                allow_agent=False
            )
        else:
            client.connect(
                hostname=credentials.host,
                port=credentials.port,
                username=credentials.username,
                password=credentials.password,
                timeout=15,
                look_for_keys=False,
                allow_agent=False
            )
        
        def execute(cmd, sudo=True):
            if sudo and credentials.username != 'root':
                cmd = f"sudo {cmd}"
            log(f"Executing: {cmd}")
            stdin, stdout, stderr = client.exec_command(cmd)
            exit_status = stdout.channel.recv_exit_status()
            out = stdout.read().decode().strip()
            err = stderr.read().decode().strip()
            
            if out: log(f"stdout: {out}")
            if err: log(f"stderr: {err}")
            
            if exit_status != 0:
                raise RuntimeError(f"Command '{cmd}' failed with exit status {exit_status}: {err}")
            return out

        # 1. Detect Arch
        log("1. Detecting architecture...")
        raw_arch = execute("uname -m", sudo=False).strip()
        arch = "amd64" if raw_arch == "x86_64" else "arm64" if raw_arch in ("aarch64", "arm64", "armv8l") else raw_arch
        log(f"Detected architecture: {arch} (raw: {raw_arch})")

        # 2. Locate Binary
        log("2. Locating local binary...")
        base_dir = Path(__file__).resolve().parent.parent / "static" / "agents"
        
        local_binary_path = None
        if base_dir.exists():
            for file in base_dir.iterdir():
                # Allow variations like 'alloy-boringcrypto-linux-amd64.zip' or 'alloy-linux-amd64.zip'
                if file.suffix == ".zip" and f"linux-{arch}" in file.name:
                    local_binary_path = file
                    break
        
        if not local_binary_path:
            raise FileNotFoundError(
                f"No Alloy binary found for arch {arch} in {base_dir}. "
                f"Please download Alloy binary to this path for offline deployment."
            )

        # 3. Upload (SFTP)
        log("3. Uploading binary...")
        with client.open_sftp() as sftp:
            sftp.put(local_binary_path, "/tmp/alloy.zip")
        log("Binary uploaded to /tmp/alloy.zip")

        # 4. Install
        log("4. Installing...")
        execute("unzip -o /tmp/alloy.zip -d /tmp/alloy_extract")
        
        # Find the binary dynamically (handles alloy-linux-{arch} or alloy-boringcrypto-linux-{arch})
        # Use find with printf to avoid potential issues with extra output
        find_cmd = "find /tmp/alloy_extract -maxdepth 1 -type f -name 'alloy-*' -printf '%p\n' | head -n 1"
        try:
            binary_path = execute(find_cmd).strip()
        except RuntimeError:
            # Fallback if printf is not supported
            find_cmd = "find /tmp/alloy_extract -maxdepth 1 -type f -name 'alloy-*' | head -n 1"
            binary_path = execute(find_cmd).strip()
        
        if not binary_path:
             raise RuntimeError(f"Could not find alloy binary in extracted archive at /tmp/alloy_extract")
             
        log(f"Found binary at: {binary_path}")
        execute(f"mv '{binary_path}' /usr/local/bin/alloy")
        execute("chmod +x /usr/local/bin/alloy")

        # 5. Configure
        log("5. Configuring...")
        
        # Ensure URLs are correctly set. 
        # If not provided, derive them from backend_url (assuming backend_url is the Nginx entry point)
        from urllib.parse import urlparse, urlunparse
        
        parsed_backend = urlparse(backend_url)
        base_url = f"{parsed_backend.scheme}://{parsed_backend.netloc}"
        
        if not prometheus_url:
            # Assume Nginx proxy at /prometheus/ -> http://prometheus:9090/
            prometheus_url = f"{base_url}/prometheus/api/v1/write"
        
        if not loki_url:
            # Assume Nginx proxy at /loki/ -> http://loki:3100/
            # Loki push endpoint is /loki/api/v1/push
            loki_url = f"{base_url}/loki/loki/api/v1/push"
            
        log(f"Using Prometheus URL: {prometheus_url}")
        log(f"Using Loki URL: {loki_url}")

        # 4.1 Check Connectivity
        log("4.1 Checking network connectivity to backend...")
        try:
            # We use curl to check if we can connect. 
            # Prometheus write endpoint expects POST, so GET might return 405 or 404, but that means connectivity is OK.
            # If it returns 'Connection refused' or 'Timed out', that's a failure.
            # We use -I (head) or just check exit code of a simple request.
            # actually prometheus write endpoint usually returns 405 on GET.
            check_cmd = f"curl -m 5 -s -o /dev/null -w '%{{http_code}}' {prometheus_url}"
            # valid HTTP codes passed: 200, 400, 404, 405. 000 is fail.
            code_str = execute(check_cmd, sudo=False).strip()
            log(f"Connectivity check to {prometheus_url}: HTTP {code_str}")
            
            if code_str == "000":
                log(f"!!! CRITICAL WARNING !!!")
                log(f"The remote server (192.168.1.228) CANNOT reach your IP (192.168.3.26).")
                log("This is almost certainly a Windows Firewall issue.")
                log("Please allow port 80 Inbound on your Windows machine.")
            else:
                log("Connectivity check passed.")
        except Exception as e:
             log(f"Connectivity check warning: {e}")

        template_dir = os.path.join(os.path.dirname(__file__), "..", "templates")
        if not os.path.exists(template_dir):
             template_dir = os.path.join(os.path.dirname(__file__), "templates")
             
        env = Environment(loader=FileSystemLoader(template_dir))
        template = env.get_template("config.alloy.j2")
        config_content = template.render(
            prometheus_push_url=prometheus_url,
            loki_push_url=loki_url,
            resource_id=resource_id,
            backend_url=backend_url
        )
        
        execute("mkdir -p /etc/alloy")
        with client.open_sftp() as sftp:
            with sftp.file("/tmp/config.alloy", "w") as f:
                f.write(config_content)
        execute("mv /tmp/config.alloy /etc/alloy/config.alloy")

        # 6. Service
        log("6. Setting up service...")
        service_content = f"""[Unit]
Description=Grafana Alloy
After=network.target

[Service]
ExecStart=/usr/local/bin/alloy run /etc/alloy/config.alloy --server.http.listen-addr=0.0.0.0:12345 --storage.path=/var/lib/alloy/data
Restart=always
User=root

[Install]
WantedBy=multi-user.target
"""
        with client.open_sftp() as sftp:
            with sftp.file("/tmp/alloy.service", "w") as f:
                f.write(service_content)
        
        execute("mkdir -p /var/lib/alloy/data")
        execute("mv /tmp/alloy.service /etc/systemd/system/alloy.service")
        execute("systemctl daemon-reload")
        execute("systemctl restart alloy")
        execute("systemctl enable alloy")

        # 7. Cleanup
        log("7. Cleaning up...")
        execute("rm -rf /tmp/alloy.zip /tmp/alloy_extract")

        # Verify status WITHOUT raising on non-zero (since inactive returns non-zero)
        log("Checking service status...")
        exit_status = -1
        try:
            status_cmd = "systemctl is-active alloy"
            if credentials.username != 'root':
                status_cmd = f"sudo {status_cmd}"
            
            stdin, stdout, stderr = client.exec_command(status_cmd)
            exit_status = stdout.channel.recv_exit_status()
            status = stdout.read().decode().strip()
        except Exception as e:
            log(f"Warning: failed to check status: {e}")
            status = "unknown"
        
        # DEBUG: Check process list
        try:
            ps_out = execute("ps aux | grep alloy | grep -v grep", sudo=False)
            log(f"DEBUG: Process list:\n{ps_out}")
        except:
            log("DEBUG: failed to get process list")

        if status == "active":
            log("Deployment successful! Alloy is active.")
            return True, "\n".join(logs)
        else:
            log(f"Deployment finished but service status is: {status} (exit code: {exit_status})")
            # Get service logs
            try:
                journal = execute("journalctl -u alloy -n 50 --no-pager", sudo=True)
                log(f"Service Logs:\n{journal}")
            except:
                log("Failed to retrieve service logs")
            return False, "\n".join(logs)

    except Exception as e:
        error_msg = f"Failed to deploy Alloy to {credentials.host}: {e}"
        logger.error(error_msg)
        logs.append(error_msg)
        return False, "\n".join(logs)
    finally:
        client.close()
