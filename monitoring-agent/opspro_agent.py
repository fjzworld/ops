#!/usr/bin/env python3
"""
OpsPro Monitoring Agent
Collects system metrics and reports to OpsPro backend
"""
import os
import sys
import time
import json
import psutil
import requests
from datetime import datetime

# Configuration (to be updated during deployment)
BACKEND_URL = os.getenv("OPSPRO_BACKEND_URL", "http://localhost/api/v1")
RESOURCE_ID = os.getenv("OPSPRO_RESOURCE_ID", None)
API_TOKEN = os.getenv("OPSPRO_API_TOKEN", None)
INTERVAL = int(os.getenv("OPSPRO_INTERVAL", "30"))  # seconds


class MetricsCollector:
    """Collects system metrics using psutil"""
    
    def __init__(self):
        self.last_net_io = None
        self.last_net_time = None
    
    @staticmethod
    def get_cpu_usage():
        """Get CPU usage percentage"""
        return psutil.cpu_percent(interval=1)
    
    @staticmethod
    def get_memory_usage():
        """Get memory usage percentage"""
        mem = psutil.virtual_memory()
        return mem.percent
    
    @staticmethod
    def get_disk_usage():
        """Get disk usage percentage for root partition"""
        disk = psutil.disk_usage('/')
        return disk.percent
    
    def get_network_speed(self):
        """Get network speed in MB/s"""
        net_io = psutil.net_io_counters()
        current_time = time.time()
        
        if self.last_net_io and self.last_net_time:
            time_delta = current_time - self.last_net_time
            bytes_sent = net_io.bytes_sent - self.last_net_io.bytes_sent
            bytes_recv = net_io.bytes_recv - self.last_net_io.bytes_recv
            
            # Convert to MB/s
            speed_out = (bytes_sent / time_delta) / (1024 * 1024)
            speed_in = (bytes_recv / time_delta) / (1024 * 1024)
        else:
            speed_out = 0.0
            speed_in = 0.0
        
        self.last_net_io = net_io
        self.last_net_time = current_time
        
        return speed_in, speed_out
    
    @staticmethod
    def get_disk_partitions():
        """Get usage for all physical and network partitions"""
        partitions = []
        # all=True to get network mounts (cifs, nfs, etc.)
        try:
            for part in psutil.disk_partitions(all=True):
                # Filter out pseudo-filesystems and uninteresting mounts
                if part.fstype in ('squashfs', 'fuse', 'tmpfs', 'devtmpfs', 'overlay', 'aufs', 'iso9660'):
                    continue
                if part.mountpoint.startswith(('/boot', '/snap', '/run', '/sys', '/dev', '/proc')):
                    continue
                if 'docker' in part.mountpoint or 'kubelet' in part.mountpoint:
                    continue
                # Windows filtering
                if part.mountpoint.startswith(('C:\\Windows', 'Program Files')):
                    # Keep C:\ but maybe filter others? Usually simple letter drives are fine.
                    pass
                    
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                    partitions.append({
                        "mountpoint": part.mountpoint,
                        "device": part.device,
                        "fstype": part.fstype,
                        "total_gb": round(usage.total / (1024**3), 2),
                        "used_gb": round(usage.used / (1024**3), 2),
                        "percent": usage.percent
                    })
                except Exception:
                    # Permission denied or stale mount
                    continue
        except Exception as e:
            print(f"[WARN] Failed to list partitions: {e}")
            
        return partitions
    
    @staticmethod
    def get_top_processes(limit=5):
        """Get top processes by CPU/memory usage"""
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                pinfo = proc.info
                processes.append({
                    'pid': pinfo['pid'],
                    'name': pinfo['name'],
                    'cpu_percent': pinfo['cpu_percent'] or 0,
                    'memory_percent': pinfo['memory_percent'] or 0
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        # Sort by CPU usage
        processes.sort(key=lambda x: x['cpu_percent'], reverse=True)
        return processes[:limit]
    
    @staticmethod
    def get_uptime():
        """Get system uptime in seconds"""
        return time.time() - psutil.boot_time()
    
    def collect_all(self):
        """Collect all metrics"""
        net_in, net_out = self.get_network_speed()
        
        return {
            "cpu_usage": self.get_cpu_usage(),
            "memory_usage": self.get_memory_usage(),
            "disk_usage": self.get_disk_usage(),
            "disk_partitions": self.get_disk_partitions(),
            "network_in": round(net_in, 2),
            "network_out": round(net_out, 2),
            "top_processes": self.get_top_processes(),
            "uptime": self.get_uptime(),
            "timestamp": datetime.utcnow().isoformat()
        }


class MetricsReporter:
    """Reports metrics to OpsPro backend"""
    
    def __init__(self, backend_url, resource_id, api_token):
        self.backend_url = backend_url.rstrip('/')
        self.resource_id = resource_id
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_token}"
        }
    
    def report(self, metrics):
        """Send metrics to backend"""
        endpoint = f"{self.backend_url}/resources/{self.resource_id}/metrics"
        
        payload = {
            "cpu_usage": metrics["cpu_usage"],
            "memory_usage": metrics["memory_usage"],
            "disk_usage": metrics["disk_usage"],
            "disk_partitions": metrics.get("disk_partitions", []),
            "network_in": metrics.get("network_in", 0),
            "network_out": metrics.get("network_out", 0),
            "top_processes": metrics.get("top_processes", [])
        }
        
        try:
            response = requests.post(
                endpoint,
                json=payload,
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                print(f"[{metrics['timestamp']}] Metrics reported successfully")
                return True
            else:
                print(f"[ERROR] Failed to report metrics: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"[ERROR] Failed to connect to backend: {e}")
            return False


def main():
    """Main agent loop"""
    if not RESOURCE_ID or not API_TOKEN:
        print("ERROR: OPSPRO_RESOURCE_ID and OPSPRO_API_TOKEN must be set")
        sys.exit(1)
    
    print(f"OpsPro Monitoring Agent started")
    print(f"Backend URL: {BACKEND_URL}")
    print(f"Resource ID: {RESOURCE_ID}")
    print(f"Report Interval: {INTERVAL}s")
    print("-" * 50)
    
    collector = MetricsCollector()
    reporter = MetricsReporter(BACKEND_URL, RESOURCE_ID, API_TOKEN)
    
    while True:
        try:
            # Collect metrics
            metrics = collector.collect_all()
            
            # Print to console with network info
            print(f"CPU: {metrics['cpu_usage']:.1f}% | "
                  f"MEM: {metrics['memory_usage']:.1f}% | "
                  f"DISK: {metrics['disk_usage']:.1f}% | "
                  f"NET: ↓{metrics['network_in']:.2f} ↑{metrics['network_out']:.2f} MB/s")
            
            # Report to backend
            reporter.report(metrics)
            
            # Wait for next interval
            time.sleep(INTERVAL)
            
        except KeyboardInterrupt:
            print("\nAgent stopped by user")
            break
        except Exception as e:
            print(f"[ERROR] Unexpected error: {e}")
            time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
