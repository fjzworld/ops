"""
Docker Container Management Service via SSH
Executes docker commands on remote servers
"""
import json
import logging
from typing import List, Optional
from pydantic import BaseModel
from app.services.resource_detector import SSHCredentials, ResourceDetector

logger = logging.getLogger(__name__)


class Container(BaseModel):
    """Docker container information"""
    id: str
    name: str
    image: str
    status: str
    state: str  # running, exited, paused, etc.
    ports: str
    created: str


class DockerService:
    """Manage Docker containers via SSH"""
    
    def __init__(self, credentials: SSHCredentials):
        self.detector = ResourceDetector(credentials)
    
    def list_containers(self, all_containers: bool = True) -> List[Container]:
        """
        List Docker containers on remote server
        
        Args:
            all_containers: If True, include stopped containers
        """
        try:
            self.detector.connect()
            
            # Use docker ps with JSON format for reliable parsing
            cmd = "docker ps --format '{{json .}}'"
            if all_containers:
                cmd = "docker ps -a --format '{{json .}}'"
            
            output = self.detector.execute_command(cmd)
            
            containers = []
            for line in output.strip().split('\n'):
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    containers.append(Container(
                        id=data.get("ID", ""),
                        name=data.get("Names", ""),
                        image=data.get("Image", ""),
                        status=data.get("Status", ""),
                        state=data.get("State", ""),
                        ports=data.get("Ports", ""),
                        created=data.get("CreatedAt", data.get("RunningFor", ""))
                    ))
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse container JSON: {line}")
                    continue
            
            return containers
        finally:
            self.detector.close()
    
    def start_container(self, container_id: str) -> bool:
        """Start a stopped container"""
        try:
            self.detector.connect()
            self.detector.execute_command(f"docker start {container_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to start container {container_id}: {e}")
            raise RuntimeError(f"启动容器失败: {e}")
        finally:
            self.detector.close()
    
    def stop_container(self, container_id: str) -> bool:
        """Stop a running container"""
        try:
            self.detector.connect()
            self.detector.execute_command(f"docker stop {container_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to stop container {container_id}: {e}")
            raise RuntimeError(f"停止容器失败: {e}")
        finally:
            self.detector.close()
    
    def restart_container(self, container_id: str) -> bool:
        """Restart a container"""
        try:
            self.detector.connect()
            self.detector.execute_command(f"docker restart {container_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to restart container {container_id}: {e}")
            raise RuntimeError(f"重启容器失败: {e}")
        finally:
            self.detector.close()
    
    def get_logs(self, container_id: str, tail: int = 100) -> str:
        """
        Get container logs
        
        Args:
            container_id: Container ID or name
            tail: Number of lines to return (default 100)
        """
        try:
            self.detector.connect()
            output = self.detector.execute_command(
                f"docker logs --tail {tail} {container_id} 2>&1"
            )
            return output
        except Exception as e:
            logger.error(f"Failed to get logs for {container_id}: {e}")
            raise RuntimeError(f"获取日志失败: {e}")
        finally:
            self.detector.close()


def get_docker_service(credentials: SSHCredentials) -> DockerService:
    """Factory function to create DockerService instance"""
    return DockerService(credentials)
