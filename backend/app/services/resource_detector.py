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
        """Establish SSH connection"""
        self.client = paramiko.SSHClient()
        # Ensure we can connect to new resources in this environment
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        try:
            if self.credentials.private_key:
                # Use private key authentication
                key = paramiko.RSAKey.from_private_key_file(self.credentials.private_key)
                self.client.connect(
                    hostname=self.credentials.host,
                    port=self.credentials.port,
                    username=self.credentials.username,
                    pkey=key,
                    timeout=10,
                    look_for_keys=False,
                    allow_agent=False
                )
            else:
                # Use password authentication
                self.client.connect(
                    hostname=self.credentials.host,
                    port=self.credentials.port,
                    username=self.credentials.username,
                    password=self.credentials.password,
                    timeout=10,
                    look_for_keys=False,
                    allow_agent=False
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

    def detect_service_name(self, mw_type: str) -> Optional[str]:
        """
        根据中间件类型自动检测服务名称
        Returns: 检测到的服务名称，如果未检测到返回 None
        """
        # 定义每种类型可能的服务名称列表
        service_candidates = {
            'mysql': ['mysqld', 'mysql'],
            'redis': ['redis-server', 'redis'],
            'nginx': ['nginx'],
            'postgresql': ['postgresql', 'postgres'],
            'mongodb': ['mongod', 'mongodb'],
        }

        candidates = service_candidates.get(mw_type, [])
        
        for svc_name in candidates:
            try:
                # 检查服务是否存在
                output = self.execute_command(f"systemctl list-unit-files {svc_name}.service 2>/dev/null | grep -q {svc_name} && echo 'found'")
                if output and 'found' in output:
                    logger.info(f"Detected service name: {svc_name} for type: {mw_type}")
                    return svc_name
            except Exception as e:
                logger.debug(f"Service {svc_name} not found: {e}")
                continue

        return None

    def control_service(self, service_name: str, action: str) -> Dict[str, any]:
        """
        控制服务 (start/stop/restart)
        Returns: {
            "success": bool,
            "message": str,
            "output": str
        }
        """
        result = {
            "success": False,
            "message": "",
            "output": ""
        }

        if action not in ["start", "stop", "restart"]:
            result["message"] = f"不支持的操作: {action}"
            return result

        try:
            self.connect()

            # 执行 systemctl 命令
            cmd = f"sudo systemctl {action} {service_name} 2>&1"
            logger.info(f"Executing: {cmd}")
            stdin, stdout, stderr = self.client.exec_command(cmd)
            output = stdout.read().decode('utf-8').strip()
            exit_status = stdout.channel.recv_exit_status()

            result["output"] = output

            if exit_status == 0:
                result["success"] = True
                result["message"] = f"服务 {service_name} {action} 成功"
            else:
                result["message"] = f"服务 {service_name} {action} 失败: {output}"

        except Exception as e:
            result["message"] = f"执行服务操作失败: {str(e)}"
            logger.error(f"Service control failed: {e}")
        finally:
            self.close()

        return result

    def verify_middleware(
        self,
        mw_type: str,
        port: int,
        service_name: str = None,
        username: str = None,
        password: str = None
    ) -> Dict[str, any]:
        """
        验证中间件配置是否正确
        Returns: {
            "success": bool,
            "port_reachable": bool,
            "service_active": bool,
            "auth_valid": bool,
            "message": str,
            "details": dict
        }
        """
        result = {
            "success": False,
            "port_reachable": False,
            "service_active": False,
            "auth_valid": False,
            "message": "",
            "details": {}
        }

        try:
            self.connect()

            # 1. 检查端口是否监听
            port_check_cmd = f"ss -tlnp | grep ':{port}' || netstat -tlnp 2>/dev/null | grep ':{port}'"
            port_output = self.execute_command(port_check_cmd)

            if port_output and str(port) in port_output:
                result["port_reachable"] = True
                result["details"]["port_info"] = port_output.strip()
            else:
                result["message"] = f"端口 {port} 未监听，请检查服务是否启动"
                return result

            # 2. 检查服务状态
            if service_name:
                try:
                    service_status = self.execute_command(f"systemctl is-active {service_name} 2>/dev/null || echo 'unknown'")
                    service_status = service_status.strip()

                    if service_status == "active":
                        result["service_active"] = True
                        result["details"]["service_status"] = "active"
                    elif service_status in ("inactive", "dead"):
                        result["details"]["service_status"] = "inactive"
                        result["message"] = f"服务 {service_name} 未运行 (状态: {service_status})"
                        return result
                    elif service_status == "failed":
                        result["details"]["service_status"] = "failed"
                        result["message"] = f"服务 {service_name} 启动失败"
                        return result
                    else:
                        # 服务名可能不存在，但端口在监听，继续验证
                        result["service_active"] = True
                        result["details"]["service_status"] = "unknown (port is listening)"
                except Exception as e:
                    result["details"]["service_check_error"] = str(e)
                    # 服务检查失败但端口在监听，继续
                    result["service_active"] = True
            else:
                # 没有服务名，尝试自动检测
                detected_service = self.detect_service_name(mw_type)
                if detected_service:
                    result["details"]["detected_service_name"] = detected_service
                    # 使用检测到的服务名检查状态
                    try:
                        service_status = self.execute_command(f"systemctl is-active {detected_service} 2>/dev/null || echo 'unknown'")
                        service_status = service_status.strip()
                        if service_status == "active":
                            result["service_active"] = True
                            result["details"]["service_status"] = "active"
                        else:
                            result["service_active"] = True
                            result["details"]["service_status"] = f"{service_status} (auto-detected)"
                    except Exception as e:
                        result["service_active"] = True
                        result["details"]["service_status"] = f"check failed (auto-detected: {detected_service})"
                else:
                    # 未检测到服务名，跳过服务检查
                    result["service_active"] = True
                    result["details"]["service_status"] = "skipped (no service name detected)"

            # 3. 验证认证信息
            if mw_type == 'mysql':
                auth_result = self._verify_mysql_auth(port, username, password)
                result["auth_valid"] = auth_result["success"]
                result["details"]["auth_test"] = auth_result
                if not auth_result["success"]:
                    result["message"] = auth_result.get("error", "MySQL认证失败")
                    return result

            elif mw_type == 'redis':
                auth_result = self._verify_redis_auth(port, password)
                result["auth_valid"] = auth_result["success"]
                result["details"]["auth_test"] = auth_result
                if not auth_result["success"]:
                    result["message"] = auth_result.get("error", "Redis认证失败")
                    return result
            else:
                # 其他类型，跳过认证验证
                result["auth_valid"] = True
                result["details"]["auth_test"] = "skipped"

            # 全部验证通过
            result["success"] = True
            result["message"] = "验证通过"

        except ConnectionError as e:
            result["message"] = f"SSH连接失败: {str(e)}"
        except Exception as e:
            result["message"] = f"验证过程出错: {str(e)}"
            logger.error(f"Middleware verification failed: {e}")
        finally:
            self.close()

        return result

    def _verify_mysql_auth(self, port: int, username: str = None, password: str = None) -> Dict[str, any]:
        """验证MySQL认证"""
        result = {"success": False, "error": ""}

        if not username:
            username = "root"

        pass_arg = f"-p'{password}'" if password else ""
        cmds = ["mysqladmin", "/usr/bin/mysqladmin", "/usr/local/mysql/bin/mysqladmin"]

        for binary in cmds:
            cmd = f"{binary} -u{username} {pass_arg} -P{port} -h127.0.0.1 status 2>&1"
            try:
                stdin, stdout, stderr = self.client.exec_command(cmd)
                output = stdout.read().decode('utf-8').strip()
                error = stderr.read().decode('utf-8').strip()

                if "Uptime" in output:
                    result["success"] = True
                    result["output"] = output
                    return result
                elif "Access denied" in output or "Access denied" in error:
                    result["error"] = "用户名或密码错误"
                    return result
            except Exception as e:
                continue

        result["error"] = "无法连接到MySQL服务，请检查配置"
        return result

    def _verify_redis_auth(self, port: int, password: str = None) -> Dict[str, any]:
        """验证Redis认证"""
        result = {"success": False, "error": ""}

        auth_arg = f"-a '{password}'" if password else ""
        cmds = ["redis-cli", "/usr/bin/redis-cli", "/usr/local/bin/redis-cli"]

        for binary in cmds:
            cmd = f"{binary} -h 127.0.0.1 -p {port} {auth_arg} ping 2>&1"
            try:
                stdin, stdout, stderr = self.client.exec_command(cmd)
                output = stdout.read().decode('utf-8').strip()

                if "PONG" in output.upper() or "pong" in output.lower():
                    result["success"] = True
                    result["output"] = output
                    return result
                elif "NOAUTH" in output or "Authentication" in output:
                    result["error"] = "Redis需要认证，请提供密码"
                    return result
                elif "WRONGPASS" in output or "invalid password" in output.lower():
                    result["error"] = "Redis密码错误"
                    return result
            except Exception as e:
                continue

        result["error"] = "无法连接到Redis服务，请检查配置"
        return result

    def detect_log_path(self, mw_type: str, service_name: str = None) -> Dict[str, any]:
        """
        自动探测中间件日志路径
        Returns: {
            "found": bool,
            "path": str or None,
            "candidates": list  # 候选路径列表
        }
        """
        result = {
            "found": False,
            "path": None,
            "candidates": []
        }

        # 确保SSH连接已建立
        need_close = False
        try:
            # 检查连接是否有效（不仅仅是 client 是否存在）
            if not self.client or not self.client.get_transport() or not self.client.get_transport().is_active():
                self.connect()
                need_close = True
        except Exception as e:
            logger.warning(f"Failed to establish SSH connection for log detection: {e}")
            return result

        try:
            if mw_type == 'mysql':
                # 方案1: 从进程参数提取 --log-error
                try:
                    ps_output = self.execute_command("ps aux | grep mysqld | grep -v grep")
                    logger.info(f"[LogDetect] MySQL ps output: {ps_output[:200] if ps_output else 'empty'}")
                    if ps_output:
                        # 尝试提取 --log-error 参数
                        log_match = re.search(r'--log-error[=\s]+([^\s]+)', ps_output)
                        if log_match:
                            log_path = log_match.group(1).strip()
                            logger.info(f"[LogDetect] Found --log-error param: {log_path}")
                            # 验证文件是否存在
                            check_cmd = f"test -f '{log_path}' && echo 'exists'"
                            if self.execute_command(check_cmd).strip() == 'exists':
                                result["found"] = True
                                result["path"] = log_path
                                result["candidates"].append(log_path)
                                logger.info(f"[LogDetect] Log file exists: {log_path}")
                except Exception as e:
                    logger.warning(f"[LogDetect] MySQL ps check failed: {e}")

                # 方案2: 检查常见路径
                common_paths = [
                    "/var/log/mysql/error.log",
                    "/var/log/mysqld.log",
                    "/var/lib/mysql/$(hostname).err",
                    "/usr/local/mysql/data/$(hostname).err"
                ]

                for path in common_paths:
                    try:
                        # 替换 $(hostname)
                        actual_path = path.replace("$(hostname)", self.execute_command("hostname"))
                        check_cmd = f"test -f '{actual_path}' && echo 'exists'"
                        exists = self.execute_command(check_cmd).strip() == 'exists'
                        logger.info(f"[LogDetect] Check path {actual_path}: {'exists' if exists else 'not found'}")
                        if exists:
                            if actual_path not in result["candidates"]:
                                result["candidates"].append(actual_path)
                                if not result["found"]:
                                    result["found"] = True
                                    result["path"] = actual_path
                    except Exception as e:
                        logger.warning(f"[LogDetect] Check path {path} failed: {e}")
                        continue

            elif mw_type == 'redis':
                # 方案1: 从配置文件提取 logfile
                try:
                    # 查找 redis 配置文件
                    config_paths = [
                        "/etc/redis/redis.conf",
                        "/etc/redis.conf",
                        "/usr/local/etc/redis/redis.conf"
                    ]
                    for config_path in config_paths:
                        try:
                            check_cmd = f"test -f '{config_path}' && echo 'exists'"
                            if self.execute_command(check_cmd).strip() == 'exists':
                                grep_cmd = f"grep '^logfile' {config_path} | head -1"
                                logfile_line = self.execute_command(grep_cmd)
                                if logfile_line and 'logfile' in logfile_line:
                                    # 解析 logfile 路径
                                    log_path = logfile_line.split('logfile')[-1].strip().strip('"').strip("'")
                                    if log_path and log_path != '""' and log_path != "''":
                                        # 验证文件是否存在
                                        check_cmd = f"test -f '{log_path}' && echo 'exists'"
                                        if self.execute_command(check_cmd).strip() == 'exists':
                                            result["found"] = True
                                            result["path"] = log_path
                                            result["candidates"].append(log_path)
                                            break
                        except Exception:
                            continue
                except Exception:
                    pass

                # 方案2: 检查常见路径
                common_paths = [
                    "/var/log/redis/redis-server.log",
                    "/var/log/redis/redis.log",
                    "/var/log/redis_6379.log",
                    "/var/log/redis/redis-6379.log"
                ]

                for path in common_paths:
                    try:
                        check_cmd = f"test -f '{path}' && echo 'exists'"
                        if self.execute_command(check_cmd).strip() == 'exists':
                            if path not in result["candidates"]:
                                result["candidates"].append(path)
                                if not result["found"]:
                                    result["found"] = True
                                    result["path"] = path
                    except Exception:
                        continue

            elif mw_type == 'sentinel':
                # Sentinel 日志通常与 Redis 类似
                common_paths = [
                    "/var/log/redis/redis-sentinel.log",
                    "/var/log/redis/sentinel.log"
                ]

                for path in common_paths:
                    try:
                        check_cmd = f"test -f '{path}' && echo 'exists'"
                        if self.execute_command(check_cmd).strip() == 'exists':
                            if path not in result["candidates"]:
                                result["candidates"].append(path)
                                if not result["found"]:
                                    result["found"] = True
                                    result["path"] = path
                    except Exception:
                        continue

        except Exception as e:
            logger.warning(f"Log path detection failed: {e}")
        finally:
            # 如果是本方法建立的连接，则关闭它
            if need_close:
                self.close()

        return result


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
