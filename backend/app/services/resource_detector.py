"""
Resource auto-detection service via SSH
Detects CPU, Memory, Disk, OS info from remote servers
"""
import paramiko
import re
import hashlib
import logging
from typing import Dict, Optional
from pydantic import BaseModel

# Setup logging
logger = logging.getLogger(__name__)


class SSHCredentials(BaseModel):
    """SSH connection credentials"""
    host: str
    port: int = 22
    username: str
    password: Optional[str] = None
    private_key: Optional[str] = None


class ServerInfo(BaseModel):
    """Detected server information"""
    hostname: str
    cpu_cores: int
    memory_gb: float
    disk_gb: float
    os_type: str
    os_version: str
    kernel_version: str


class LoggingMissingHostKeyPolicy(paramiko.MissingHostKeyPolicy):
    """
    SSH host key policy that logs warnings about unknown hosts.
    This is more secure than AutoAddPolicy as it records the host fingerprint.
    In production, consider using RejectPolicy and managing known_hosts properly.
    """
    
    def missing_host_key(self, client, hostname, key):
        fingerprint = hashlib.sha256(key.asbytes()).hexdigest()[:16]
        key_type = key.get_name()
        logger.warning(
            f"SSH: Unknown host key for {hostname}. "
            f"Key type: {key_type}, Fingerprint: {fingerprint}. "
            f"Please verify this is the expected server before proceeding."
        )
        # In production, you might want to raise an exception here instead
        # raise paramiko.SSHException(f"Unknown host key for {hostname}")


class ResourceDetector:
    """Auto-detect server resources via SSH"""
    
    def __init__(self, credentials: SSHCredentials):
        self.credentials = credentials
        self.client: Optional[paramiko.SSHClient] = None
    
    def connect(self) -> None:
        """Establish SSH connection with improved host key verification"""
        self.client = paramiko.SSHClient()
        # Use logging policy instead of AutoAddPolicy for better security auditing
        self.client.set_missing_host_key_policy(LoggingMissingHostKeyPolicy())
        
        try:
            if self.credentials.private_key:
                # Use private key authentication
                key = paramiko.RSAKey.from_private_key_file(self.credentials.private_key)
                self.client.connect(
                    hostname=self.credentials.host,
                    port=self.credentials.port,
                    username=self.credentials.username,
                    pkey=key,
                    timeout=10
                )
            else:
                # Use password authentication
                self.client.connect(
                    hostname=self.credentials.host,
                    port=self.credentials.port,
                    username=self.credentials.username,
                    password=self.credentials.password,
                    timeout=10
                )
        except Exception as e:
            raise ConnectionError(f"SSH connection failed: {str(e)}")
    
    def execute_command(self, command: str) -> str:
        """Execute command on remote server"""
        if not self.client:
            raise RuntimeError("SSH client not connected")
        
        stdin, stdout, stderr = self.client.exec_command(command)
        output = stdout.read().decode('utf-8').strip()
        error = stderr.read().decode('utf-8').strip()
        
        if error and "command not found" in error.lower():
            raise RuntimeError(f"Command failed: {error}")
        
        return output
    
    def detect_hostname(self) -> str:
        """Get server hostname"""
        return self.execute_command("hostname")
    
    def detect_cpu_cores(self) -> int:
        """Detect CPU core count"""
        try:
            # Linux: nproc or /proc/cpuinfo
            output = self.execute_command("nproc")
            return int(output)
        except:
            try:
                output = self.execute_command("grep -c ^processor /proc/cpuinfo")
                return int(output)
            except:
                # Fallback: assume 1 core
                return 1
    
    def detect_memory_gb(self) -> float:
        """Detect total memory in GB"""
        try:
            # Linux: Read from /proc/meminfo
            output = self.execute_command("grep MemTotal /proc/meminfo | awk '{print $2}'")
            mem_kb = int(output)
            return round(mem_kb / (1024 * 1024), 2)  # Convert KB to GB
        except:
            try:
                # Alternative: use free command
                output = self.execute_command("free -g | grep Mem | awk '{print $2}'")
                return float(output)
            except:
                return 0.0
    
    def detect_disk_gb(self) -> float:
        """Detect total disk space in GB"""
        try:
            # Get root partition size
            output = self.execute_command("df -BG / | tail -1 | awk '{print $2}' | sed 's/G//'")
            return float(output)
        except:
            return 0.0
    
    def detect_os_info(self) -> Dict[str, str]:
        """Detect OS type and version"""
        try:
            # Try /etc/os-release (most modern Linux distros)
            output = self.execute_command("cat /etc/os-release")
            
            os_type = "Linux"
            os_version = "Unknown"
            
            # Parse os-release
            for line in output.split('\n'):
                if line.startswith('NAME='):
                    os_type = line.split('=')[1].strip('"')
                elif line.startswith('VERSION='):
                    os_version = line.split('=')[1].strip('"')
            
            # Get kernel version
            kernel_version = self.execute_command("uname -r")
            
            return {
                "os_type": os_type,
                "os_version": os_version,
                "kernel_version": kernel_version
            }
        except:
            # Fallback: use uname
            try:
                uname_output = self.execute_command("uname -a")
                return {
                    "os_type": "Linux" if "Linux" in uname_output else "Unix",
                    "os_version": "Unknown",
                    "kernel_version": uname_output.split()[2] if len(uname_output.split()) > 2 else "Unknown"
                }
            except:
                return {
                    "os_type": "Unknown",
                    "os_version": "Unknown",
                    "kernel_version": "Unknown"
                }
    
    def probe(self) -> ServerInfo:
        """
        Full server detection process
        Returns complete server information
        """
        try:
            self.connect()
            
            hostname = self.detect_hostname()
            cpu_cores = self.detect_cpu_cores()
            memory_gb = self.detect_memory_gb()
            disk_gb = self.detect_disk_gb()
            os_info = self.detect_os_info()
            
            return ServerInfo(
                hostname=hostname,
                cpu_cores=cpu_cores,
                memory_gb=memory_gb,
                disk_gb=disk_gb,
                os_type=os_info["os_type"],
                os_version=os_info["os_version"],
                kernel_version=os_info["kernel_version"]
            )
        finally:
            self.close()
    
    def get_metrics_and_status(self, mw_type: str, port: int, service_name: str, username: str = None, password: str = None) -> Dict[str, any]:
        """Collect both status and metrics in a single SSH session"""
        result = {"status": "unknown"}
        try:
            self.connect()
            
            # 1. Check Status
            if service_name:
                try:
                    status_out = self.execute_command(f"systemctl is-active {service_name}")
                    status_out = status_out.strip() if status_out else "unknown"
                    if status_out == "active":
                        result["status"] = "active"
                    elif status_out in ("inactive", "dead"):
                        result["status"] = "inactive"
                    elif status_out in ("failed", "error"):
                        result["status"] = "error"
                    else:
                        result["status"] = "stopped"
                except Exception as e:
                    logger.warning(f"Status check failed: {e}")
                    result["status"] = "stopped"
            else:
                result["status"] = "active" # Assume active if no service name

            # 2. Collect Metrics if active
            if result["status"] == "active":
                metrics = {}
                
                if mw_type == 'mysql':
                    pass_arg = f"-p'{password}'" if password else ""
                    cmds = ["mysqladmin", "/usr/bin/mysqladmin", "/usr/local/mysql/bin/mysqladmin"]
                    output = ""
                    for binary in cmds:
                        cmd = f"{binary} -u{username} {pass_arg} -P{port} -h127.0.0.1 status"
                        try:
                            # Direct execute_command call reused
                            stdin, stdout, stderr = self.client.exec_command(cmd)
                            out_str = stdout.read().decode('utf-8').strip()
                            if out_str and "Uptime" in out_str:
                                output = out_str
                                break
                        except Exception:
                            continue
                    
                    if output:
                        import re
                        uptime = re.search(r'Uptime:\s+(\d+)', output)
                        if uptime: metrics['uptime'] = int(uptime.group(1))
                        
                        threads = re.search(r'Threads:\s+(\d+)', output)
                        if threads: metrics['threads'] = int(threads.group(1))
                        
                        open_tables = re.search(r'Open tables:\s+(\d+)', output)
                        if open_tables: metrics['open_tables'] = int(open_tables.group(1))
                        
                        qps = re.search(r'Queries per second avg:\s+([\d\.]+)', output)
                        if qps: metrics['qps'] = float(qps.group(1))
                        metrics['queries_per_second_avg'] = metrics.get('qps')
                
                elif mw_type == 'redis':
                    auth_arg = f"-a '{password}'" if password else ""
                    cmds = ["redis-cli", "/usr/bin/redis-cli", "/usr/local/bin/redis-cli"]
                    output = ""
                    for binary in cmds:
                        cmd = f"{binary} -h 127.0.0.1 -p {port} {auth_arg} info"
                        try:
                            stdin, stdout, stderr = self.client.exec_command(cmd)
                            out_str = stdout.read().decode('utf-8').strip()
                            if out_str and ("redis_version" in out_str or "connected_clients" in out_str):
                                output = out_str
                                break
                        except Exception:
                            continue

                    if output:
                        for line in output.splitlines():
                            if ':' in line:
                                key, val = line.split(':', 1)
                                key = key.strip()
                                val = val.strip()
                                if key == "connected_clients":
                                    metrics["connected_clients"] = int(val)
                                elif key == "instantaneous_ops_per_sec":
                                    metrics["instantaneous_ops_per_sec"] = int(val)
                                elif key == "used_memory_human":
                                    metrics["used_memory_human"] = val
                                elif key == "uptime_in_seconds":
                                    metrics["uptime_in_seconds"] = int(val)
                
                result.update(metrics)
                
            return result
            
        except Exception as e:
            logger.error(f"Combined metrics collection failed: {e}")
            return result
        finally:
            self.close()
    
    def close(self) -> None:
        """Close SSH connection"""
        if self.client:
            self.client.close()


def probe_server(credentials: SSHCredentials) -> ServerInfo:
    """
    Convenience function to probe a server
    
    Args:
        credentials: SSH connection credentials
    
    Returns:
        ServerInfo: Detected server information
    
    Raises:
        ConnectionError: If SSH connection fails
        RuntimeError: If detection commands fail
    """
    detector = ResourceDetector(credentials)
    return detector.probe()
