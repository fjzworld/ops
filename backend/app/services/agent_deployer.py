"""
Service to deploy monitoring agent to remote servers
"""
import os
import time
from typing import Optional
from app.services.resource_detector import SSHCredentials
import paramiko


AGENT_SCRIPT = """#!/usr/bin/env python3
# OpsPro Monitoring Agent - Hybrid Mode (psutil + Native Linux)
import os, sys, time, json, socket
import subprocess
from datetime import datetime

BACKEND_URL = "__BACKEND_URL__"
RESOURCE_ID = "__RESOURCE_ID__"
API_TOKEN = "__API_TOKEN__"
INTERVAL = 30

# ===== 依赖库处理 =====
try:
    import requests
except ImportError:
    requests = None

try:
    import psutil
except ImportError:
    psutil = None

# ===== HTTP 客户端封装 (兼容无 requests 环境) =====
class HttpClient:
    @staticmethod
    def post(url, json_data, token):
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        # 方式 1: 使用 requests (首选)
        if requests:
            try:
                resp = requests.post(url, json=json_data, headers=headers, timeout=10)
                return resp.status_code
            except Exception as e:
                print(f"[HttpError] {e}")
                return 0
        
        # 方式 2: 使用 urllib (标准库兜底)
        else:
            import urllib.request
            import urllib.error
            try:
                data = json.dumps(json_data).encode('utf-8')
                req = urllib.request.Request(url, data=data, headers=headers, method='POST')
                with urllib.request.urlopen(req, timeout=10) as f:
                    return f.getcode()
            except urllib.error.HTTPError as e:
                print(f"[HttpError] {e.code}: {e.read().decode()}")
                return e.code
            except Exception as e:
                print(f"[HttpError] {e}")
                return 0

# ===== Linux 原生采集器 (无 psutil 依赖) =====
class LinuxNativeCollector:
    def __init__(self):
        self.last_cpu_times = self._get_cpu_times()
        self.last_net_io = self._get_net_io()
    
    def _get_cpu_times(self):
        try:
            with open('/proc/stat', 'r') as f:
                line = f.readline()
                if line.startswith('cpu'):
                    parts = line.split()[1:]
                    return [float(x) for x in parts]
        except:
            return None
            
    def get_cpu_usage(self):
        current_times = self._get_cpu_times()
        if not self.last_cpu_times or not current_times:
            self.last_cpu_times = current_times
            return 0.0
        delta = [c - l for c, l in zip(current_times, self.last_cpu_times)]
        self.last_cpu_times = current_times
        idle_time = delta[3]
        total_time = sum(delta)
        if total_time == 0: return 0.0
        return round(100.0 * (1.0 - idle_time / total_time), 1)

    def get_memory_usage(self):
        try:
            mem = {}
            with open('/proc/meminfo', 'r') as f:
                for line in f:
                    parts = line.split(':')
                    if len(parts) == 2:
                        key = parts[0].strip()
                        val = int(parts[1].split()[0])
                        mem[key] = val
            total = mem.get('MemTotal', 1)
            free = mem.get('MemFree', 0)
            buffers = mem.get('Buffers', 0)
            cached = mem.get('Cached', 0)
            available = mem.get('MemAvailable', free + buffers + cached)
            used = total - available
            return round(100.0 * used / total, 1)
        except:
            return 0.0

    def get_disk_partitions(self):
        '''采集所有物理分区和网络挂载，排除系统分区'''
        partitions = []
        try:
            # 获取所有挂载点
            mounts = {}
            with open('/proc/mounts', 'r') as f:
                for line in f:
                    parts = line.split()
                    if len(parts) >= 3:
                        # device, mountpoint, fstype
                        mounts[parts[1]] = {'device': parts[0], 'fstype': parts[2]}
            
            for mp, info in mounts.items():
                fstype = info['fstype']
                # Blacklist system filesystems
                if fstype in ('proc', 'sysfs', 'devtmpfs', 'devpts', 'tmpfs', 'overlay', 'squashfs', 'iso9660', 'autofs', 'cgroup', 'pstore', 'bpf', 'hugetlbfs', 'mqueue'):
                    continue
                if mp.startswith(('/proc', '/sys', '/dev', '/boot', '/run', '/var/lib/docker', '/var/lib/kubelet', '/var/lib/containerd', '/snap')):
                    continue
                
                try:
                    stat = os.statvfs(mp)
                    total = stat.f_blocks * stat.f_frsize
                    # Ignore tiny partitions (<100MB)
                    if total < 100 * 1024 * 1024:
                        continue

                    used = (stat.f_blocks - stat.f_bfree) * stat.f_frsize
                    
                    partitions.append({
                        "mountpoint": mp,
                        "device": info['device'],
                        "fstype": fstype,
                        "total_gb": round(total / (1024**3), 2),
                        "used_gb": round(used / (1024**3), 2),
                        "percent": round(100.0 * used / total, 1) if total > 0 else 0.0
                    })
                except:
                    continue
        except:
            pass
        return sorted(partitions, key=lambda x: x['mountpoint'])

    def _get_net_io(self):
        try:
            bytes_recv = 0
            bytes_sent = 0
            with open('/proc/net/dev', 'r') as f:
                lines = f.readlines()[2:]
                for line in lines:
                    parts = line.split(':')
                    if len(parts) == 2:
                        data = parts[1].split()
                        if parts[0].strip() != 'lo':
                            bytes_recv += int(data[0])
                            bytes_sent += int(data[8])
            return (bytes_recv, bytes_sent)
        except:
            return (0, 0)

    def get_network_rate_sample(self):
        r1, s1 = self._get_net_io()
        time.sleep(1)
        r2, s2 = self._get_net_io()
        return {
            "network_in": round((r2 - r1) / 1024 / 1024, 2),
            "network_out": round((s2 - s1) / 1024 / 1024, 2)
        }

    def get_top_processes(self):
        try:
            cmd = "ps -eo pid,comm,%cpu,%mem --sort=-%cpu | head -n 6"
            output = subprocess.check_output(cmd, shell=True).decode('utf-8')
            lines = output.strip().split('\\n')[1:]
            processes = []
            for line in lines:
                parts = line.split()
                if len(parts) >= 4:
                    processes.append({
                        "pid": int(parts[0]),
                        "name": parts[1],
                        "cpu_percent": float(parts[2]),
                        "memory_percent": float(parts[3])
                    })
            return processes
        except:
            return []

# ===== psutil 采集器 =====
class PsutilCollector:
    def get_disk_partitions(self):
        '''采集所有物理分区和网络挂载，排除系统分区'''
        partitions = []
        try:
            # all=True ensures network mounts are included
            for part in psutil.disk_partitions(all=True):
                # Blacklist system filesystems
                if part.fstype in ('squashfs', 'fuse', 'tmpfs', 'devtmpfs', 'overlay', 'aufs', 'iso9660', 'autofs', 'cgroup', 'tracefs'):
                    continue
                if part.mountpoint.startswith(('/boot', '/snap', '/run', '/sys', '/dev', '/proc', '/var/lib/docker', '/var/lib/kubelet', '/var/lib/containerd')):
                    continue
                
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                    # Ignore tiny partitions (<100MB)
                    if usage.total < 100 * 1024 * 1024:
                        continue
                        
                    partitions.append({
                        "mountpoint": part.mountpoint,
                        "device": part.device,
                        "fstype": part.fstype,
                        "total_gb": round(usage.total / (1024**3), 2),
                        "used_gb": round(usage.used / (1024**3), 2),
                        "percent": usage.percent
                    })
                except:
                    continue
        except:
            pass
        return sorted(partitions, key=lambda x: x['mountpoint'])

    def collect_all(self):
        net_start = psutil.net_io_counters()
        time.sleep(1)
        net_end = psutil.net_io_counters()
        procs = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                pinfo = proc.info
                if pinfo['cpu_percent']: procs.append(pinfo)
            except: pass
        procs.sort(key=lambda x: x['cpu_percent'], reverse=True)
        return {
            "cpu_usage": psutil.cpu_percent(interval=0),
            "memory_usage": psutil.virtual_memory().percent,
            "disk_usage": psutil.disk_usage('/').percent,
            "disk_partitions": self.get_disk_partitions(),
            "network_in": round((net_end.bytes_recv - net_start.bytes_recv) / 1024 / 1024, 2),
            "network_out": round((net_end.bytes_sent - net_start.bytes_sent) / 1024 / 1024, 2),
            "top_processes": procs[:5]
        }

def run_agent():
    print(f"OpsPro Agent started. Backend: {BACKEND_URL}")
    print(f"Mode: {'psutil' if psutil else 'Native Linux'}")
    
    if not psutil:
        collector = LinuxNativeCollector()
        def collect():
            net = collector.get_network_rate_sample()
            return {
                "cpu_usage": collector.get_cpu_usage(),
                "memory_usage": collector.get_memory_usage(),
                "disk_usage": collector.get_disk_usage(),
                "disk_partitions": collector.get_disk_partitions(),
                "network_in": net['network_in'],
                "network_out": net['network_out'],
                "top_processes": collector.get_top_processes()
            }
    else:
        c = PsutilCollector()
        collect = c.collect_all

    while True:
        try:
            data = collect()
            data["timestamp"] = datetime.utcnow().isoformat()
            status = HttpClient.post(f"{BACKEND_URL}/resources/{RESOURCE_ID}/metrics", data, API_TOKEN)
            print(f"Reported metrics. CPU: {data['cpu_usage']}% | Status: {status}")
            time.sleep(INTERVAL - 1) 
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(INTERVAL)

if __name__ == "__main__":
    run_agent()
"""

SYSTEMD_SERVICE = """[Unit]
Description=OpsPro Monitoring Agent
After=network.target

[Service]
Type=simple
User=root
ExecStart=/usr/bin/python3 /opt/opspro/agent.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
"""


class AgentDeployer:
    """Deploy monitoring agent to remote servers"""
    
    def __init__(self, credentials: SSHCredentials, resource_id: int, api_token: str, backend_url: str):
        self.credentials = credentials
        self.resource_id = resource_id
        self.api_token = api_token
        self.backend_url = backend_url
        self.client: Optional[paramiko.SSHClient] = None
    
    def connect(self):
        """Establish SSH connection"""
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        if self.credentials.private_key:
            key = paramiko.RSAKey.from_private_key_file(self.credentials.private_key)
            self.client.connect(
                hostname=self.credentials.host,
                port=self.credentials.port,
                username=self.credentials.username,
                pkey=key,
                timeout=10
            )
        else:
            self.client.connect(
                hostname=self.credentials.host,
                port=self.credentials.port,
                username=self.credentials.username,
                password=self.credentials.password,
                timeout=10
            )
    
    def execute(self, command: str) -> str:
        """Execute command on remote server"""
        if not self.client:
            raise RuntimeError("SSH client not connected")
        
        stdin, stdout, stderr = self.client.exec_command(command)
        return stdout.read().decode('utf-8').strip()
    
    def deploy(self) -> bool:
        """
        Deploy agent to remote server (Offline Mode)
        Steps:
        1. Download Python dependencies as wheel files
        2. Upload dependencies and agent script
        3. Set up systemd service
        4. Start agent
        """
        try:
            self.connect()
            
            # Step 1: Prepare offline dependencies
            print("准备离线依赖包...")
            wheels_dir = self._prepare_offline_packages()
            
            # Step 2: Create agent directory
            print("创建 Agent 目录...")
            self.execute("mkdir -p /opt/opspro/wheels")
            
            # Step 3: Upload dependencies
            print("上传离线依赖包...")
            sftp = self.client.open_sftp()
            
            if wheels_dir and os.path.exists(wheels_dir):
                for wheel_file in os.listdir(wheels_dir):
                    local_path = os.path.join(wheels_dir, wheel_file)
                    remote_path = f"/opt/opspro/wheels/{wheel_file}"
                    sftp.put(local_path, remote_path)
                    print(f"  上传: {wheel_file}")
            
            # Step 4: Upload agent script
            print("上传 Agent 脚本...")
            # Use replace to avoid format string issues with curly braces in script
            agent_content = AGENT_SCRIPT.replace(
                "__BACKEND_URL__", self.backend_url
            ).replace(
                "__RESOURCE_ID__", str(self.resource_id)
            ).replace(
                "__API_TOKEN__", self.api_token
            )
            
            with sftp.file('/opt/opspro/agent.py', 'w') as f:
                f.write(agent_content)
            sftp.chmod('/opt/opspro/agent.py', 0o755)
            
            # Step 5: Create systemd service
            print("创建 systemd 服务...")
            with sftp.file('/etc/systemd/system/opspro-agent.service', 'w') as f:
                f.write(SYSTEMD_SERVICE)
            sftp.close()
            
            # Step 6: Install dependencies (optional)
            print("尝试安装依赖 (可选)...")
            try:
                # 尝试安装，但忽略错误
                install_cmd = "python3 -m pip install --no-index --find-links /opt/opspro/wheels psutil requests 2>/dev/null || python3 -m pip install psutil requests"
                self.execute(install_cmd)
            except Exception as e:
                print(f"依赖安装失败，Agent 将尝试以原生模式运行: {e}")
            
            # Step 7: Enable and start service
            print("启动 Agent 服务...")
            self.execute("systemctl daemon-reload")
            self.execute("systemctl enable opspro-agent")
            self.execute("systemctl restart opspro-agent")
            
            # Verify service is running
            time.sleep(2)  # Wait for service to start
            status = self.execute("systemctl is-active opspro-agent")
            if status == "active":
                print("✓ Agent 部署并启动成功！")
                return True
            else:
                print(f"⚠ Agent 服务状态: {status}")
                # 查看日志
                logs = self.execute("journalctl -u opspro-agent -n 20 --no-pager")
                print(f"服务日志:\n{logs}")
                return False
            
        except Exception as e:
            print(f"部署失败: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            if self.client:
                self.client.close()
    
    def _prepare_offline_packages(self) -> Optional[str]:
        """
        Download Python packages as wheels for offline installation
        Returns: Path to wheels directory
        """
        import subprocess
        import tempfile
        
        wheels_dir = os.path.join(tempfile.gettempdir(), "opspro_wheels")
        os.makedirs(wheels_dir, exist_ok=True)
        
        try:
            # 下载 psutil 和 requests 及其依赖
            print(f"  下载依赖到: {wheels_dir}")
            subprocess.run(
                ["pip3", "download", "-d", wheels_dir, "psutil", "requests"],
                check=True,
                capture_output=True,
                timeout=60
            )
            print(f"  ✓ 依赖包下载完成")
            return wheels_dir
        except subprocess.TimeoutExpired:
            print("  ⚠ 下载超时，将使用在线安装模式")
            return None
        except subprocess.CalledProcessError as e:
            print(f"  ⚠ 下载失败: {e}，将使用在线安装模式")
            return None
        except FileNotFoundError:
            print("  ⚠ pip3 未找到，将使用在线安装模式")
            return None
    
    def uninstall(self) -> bool:
        """
        Uninstall agent from remote server
        Steps:
        1. Stop the service
        2. Disable the service
        3. Remove service file
        4. Remove agent files
        5. Clean up systemd
        """
        try:
            self.connect()
            
            print("正在停止 Agent 服务...")
            try:
                self.execute("systemctl stop opspro-agent")
                print("  ✓ 服务已停止")
            except Exception as e:
                print(f"  ⚠ 停止服务失败（可能未运行）: {e}")
            
            print("正在禁用 Agent 服务...")
            try:
                self.execute("systemctl disable opspro-agent")
                print("  ✓ 服务已禁用")
            except Exception as e:
                print(f"  ⚠ 禁用服务失败: {e}")
            
            print("正在删除服务配置文件...")
            try:
                self.execute("rm -f /etc/systemd/system/opspro-agent.service")
                print("  ✓ 服务文件已删除")
            except Exception as e:
                print(f"  ⚠ 删除服务文件失败: {e}")
            
            print("正在删除 Agent 目录...")
            try:
                self.execute("rm -rf /opt/opspro")
                print("  ✓ Agent 目录已删除")
            except Exception as e:
                print(f"  ⚠ 删除 Agent 目录失败: {e}")
            
            print("正在重新加载 systemd...")
            try:
                self.execute("systemctl daemon-reload")
                print("  ✓ systemd 已重新加载")
            except Exception as e:
                print(f"  ⚠ 重新加载 systemd 失败: {e}")
            
            print("✓ Agent 卸载完成！")
            return True
            
        except Exception as e:
            print(f"⚠ 卸载过程中出现错误: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            if self.client:
                self.client.close()


def deploy_agent(
    credentials: SSHCredentials,
    resource_id: int,
    api_token: str,
    backend_url: str
) -> bool:
    """
    Convenience function to deploy agent
    
    Args:
        credentials: SSH credentials
        resource_id: Resource ID in database
        api_token: API token for authentication
        backend_url: Backend URL for metrics reporting
    
    Returns:
        bool: True if deployment successful
    """
    deployer = AgentDeployer(credentials, resource_id, api_token, backend_url)
    return deployer.deploy()


def uninstall_agent(credentials: SSHCredentials) -> bool:
    """
    Convenience function to uninstall agent
    
    Args:
        credentials: SSH credentials
    
    Returns:
        bool: True if uninstallation successful
    """
    deployer = AgentDeployer(credentials, resource_id=0, api_token="", backend_url="")
    return deployer.uninstall()
