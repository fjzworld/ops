import uuid
import asyncio
import logging
import zipfile
import tarfile
import tempfile
from pathlib import Path
from typing import List, Tuple, Optional
from datetime import datetime

import paramiko

from app.core.ssh import create_secure_client
from app.models.resource import Resource
from app.services.credential_service import CredentialService
from app.schemas.deploy import DeployResult, DeployStepLog

logger = logging.getLogger(__name__)

# Upload temp directory
UPLOAD_DIR = Path(tempfile.gettempdir()) / "ops_deploy_uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# Remote paths on target servers
NGINX_BASE_DIR = "/usr/local/nginx"
NGINX_HTML_DIR = f"{NGINX_BASE_DIR}/html"
NGINX_BACKUP_DIR = f"{NGINX_BASE_DIR}/backup"
NGINX_CONTAINER_NAME = "start_nginx"


class DeployService:

    @staticmethod
    def save_upload(file_content: bytes, filename: str) -> Tuple[str, str]:
        """Save uploaded file, return (file_id, saved_path)"""
        file_id = uuid.uuid4().hex[:12]
        if filename.endswith('.tar.gz') or filename.endswith('.tgz'):
            ext = '.tar.gz'
        elif filename.endswith('.zip'):
            ext = '.zip'
        else:
            raise ValueError("Only .zip and .tar.gz files are supported")

        save_path = UPLOAD_DIR / f"{file_id}{ext}"
        save_path.write_bytes(file_content)
        return file_id, str(save_path)

    @staticmethod
    def validate_package(file_path: str) -> Tuple[bool, str]:
        """Validate that the package contains index.html"""
        try:
            if file_path.endswith('.zip'):
                with zipfile.ZipFile(file_path, 'r') as zf:
                    names = zf.namelist()
            elif file_path.endswith('.tar.gz') or file_path.endswith('.tgz'):
                with tarfile.open(file_path, 'r:gz') as tf:
                    names = tf.getnames()
            else:
                return False, "Unsupported file format"

            has_index = any(n.endswith('index.html') for n in names)
            if not has_index:
                return False, "Package does not contain index.html"
            return True, "Package is valid"
        except Exception as e:
            return False, f"Failed to validate package: {str(e)}"

    @staticmethod
    def get_upload_path(file_id: str) -> Optional[str]:
        """Find uploaded file by file_id"""
        for ext in ['.zip', '.tar.gz']:
            path = UPLOAD_DIR / f"{file_id}{ext}"
            if path.exists():
                return str(path)
        return None

    @staticmethod
    def cleanup_upload(file_id: str):
        """Remove uploaded file"""
        for ext in ['.zip', '.tar.gz']:
            path = UPLOAD_DIR / f"{file_id}{ext}"
            if path.exists():
                path.unlink()

    @staticmethod
    async def deploy_to_servers(
        file_path: str,
        resources: List[Resource],
        restart_keepalived: bool = False
    ) -> List[DeployResult]:
        """Deploy frontend code to multiple servers in parallel"""
        tasks = [
            DeployService._deploy_single(file_path, resource, restart_keepalived)
            for resource in resources
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        deploy_results: List[DeployResult] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                deploy_results.append(DeployResult(
                    server=resources[i].ip_address or resources[i].name,
                    resource_id=resources[i].id,
                    success=False,
                    error=str(result)
                ))
            else:
                deploy_results.append(result)

        return deploy_results

    @staticmethod
    async def _deploy_single(
        file_path: str,
        resource: Resource,
        restart_keepalived: bool
    ) -> DeployResult:
        """Deploy to a single server via SSH"""
        server_name = resource.ip_address or resource.name
        steps: List[DeployStepLog] = []

        def step_log(step: str, status: str, message: str = ""):
            steps.append(DeployStepLog(server=server_name, step=step, status=status, message=message))
            if status == "failed":
                logger.error(f"[Deploy:{server_name}] {step}: {message}")
            else:
                logger.info(f"[Deploy:{server_name}] {step}: {status} {message}")

        credentials = CredentialService.get_ssh_credentials(resource)
        client = create_secure_client()

        try:
            connect_kwargs = {
                "hostname": credentials.host,
                "port": credentials.port,
                "username": credentials.username,
                "timeout": 15,
                "look_for_keys": False,
                "allow_agent": False,
            }
            if credentials.private_key:
                connect_kwargs["pkey"] = paramiko.RSAKey.from_private_key_file(credentials.private_key)
            else:
                connect_kwargs["password"] = credentials.password

            client.connect(**connect_kwargs)
            step_log("SSH连接", "success")

            def execute(cmd: str) -> str:
                if credentials.username != 'root':
                    cmd = f"sudo {cmd}"
                stdin, stdout, stderr = client.exec_command(cmd)
                exit_status = stdout.channel.recv_exit_status()
                out = stdout.read().decode().strip()
                err = stderr.read().decode().strip()
                if exit_status != 0:
                    raise RuntimeError(f"Command failed (exit {exit_status}): {err or out}")
                return out

            # 1. Create backup directory
            execute(f"mkdir -p {NGINX_BACKUP_DIR}")

            # 2. Backup current code
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"html_{timestamp}.tar.gz"
            try:
                execute(f"tar -czf {NGINX_BACKUP_DIR}/{backup_name} -C {NGINX_BASE_DIR} html/")
                step_log("备份当前代码", "success", backup_name)
            except Exception as e:
                step_log("备份当前代码", "failed", str(e))
                return DeployResult(
                    server=server_name, resource_id=resource.id,
                    success=False, steps=steps, error="Backup failed, deployment aborted"
                )

            # 3. Clean old backups (older than 3 days)
            try:
                execute(f"find {NGINX_BACKUP_DIR} -name 'html_*.tar.gz' -mtime +3 -delete")
                step_log("清理旧备份", "success")
            except Exception:
                step_log("清理旧备份", "success", "No old backups to clean")

            # 4. Upload new package
            remote_tmp = f"/tmp/deploy_{uuid.uuid4().hex[:8]}"
            try:
                with client.open_sftp() as sftp:
                    sftp.put(file_path, f"{remote_tmp}.pkg")
                step_log("上传代码包", "success")
            except Exception as e:
                step_log("上传代码包", "failed", str(e))
                return DeployResult(
                    server=server_name, resource_id=resource.id,
                    success=False, steps=steps, error="Upload failed"
                )

            # 5. Clear html and extract
            try:
                execute(f"rm -rf {NGINX_HTML_DIR}/*")
                extract_id = uuid.uuid4().hex[:8]
                extract_dir = f"/tmp/deploy_extract_{extract_id}"

                if file_path.endswith('.zip'):
                    execute(f"unzip -o {remote_tmp}.pkg -d {extract_dir}")
                else:
                    execute(f"mkdir -p {extract_dir}")
                    execute(f"tar -xzf {remote_tmp}.pkg -C {extract_dir}")

                # Check if index.html is at root or in a subdirectory
                check = execute(
                    f"if [ -f {extract_dir}/index.html ]; then echo 'root'; "
                    f"else ls -d {extract_dir}/*/index.html 2>/dev/null | head -1; fi"
                )
                if check == 'root':
                    execute(f"cp -a {extract_dir}/* {NGINX_HTML_DIR}/")
                else:
                    subdir = check.rsplit('/index.html', 1)[0]
                    execute(f"cp -a {subdir}/* {NGINX_HTML_DIR}/")

                execute(f"rm -rf {extract_dir} {remote_tmp}.pkg")
                step_log("解压并替换代码", "success")
            except Exception as e:
                step_log("解压并替换代码", "failed", str(e))
                # Auto rollback
                try:
                    execute(f"rm -rf {NGINX_HTML_DIR}/*")
                    execute(f"tar -xzf {NGINX_BACKUP_DIR}/{backup_name} -C {NGINX_BASE_DIR}")
                    step_log("自动回滚", "success", f"已回滚到 {backup_name}")
                except Exception:
                    step_log("自动回滚", "failed", "回滚也失败了，请手动处理")
                return DeployResult(
                    server=server_name, resource_id=resource.id,
                    success=False, steps=steps, error="Extract failed"
                )

            # 6. Restart Nginx container
            try:
                execute(f"cd {NGINX_BASE_DIR} && docker-compose restart {NGINX_CONTAINER_NAME}")
                step_log("重启Nginx容器", "success")
            except Exception as e:
                step_log("重启Nginx容器", "failed", str(e))
                return DeployResult(
                    server=server_name, resource_id=resource.id,
                    success=False, steps=steps, error="Nginx restart failed"
                )

            # 7. Restart keepalived (if requested)
            if restart_keepalived:
                try:
                    execute("systemctl restart keepalived")
                    step_log("重启keepalived", "success")
                except Exception as e:
                    step_log("重启keepalived", "failed", str(e))

            return DeployResult(server=server_name, resource_id=resource.id, success=True, steps=steps)

        except Exception as e:
            step_log("部署异常", "failed", str(e))
            return DeployResult(
                server=server_name, resource_id=resource.id,
                success=False, steps=steps, error=str(e)
            )
        finally:
            client.close()

    @staticmethod
    async def get_backups(resource: Resource) -> List[dict]:
        """Get backup list from remote server"""
        credentials = CredentialService.get_ssh_credentials(resource)
        client = create_secure_client()

        try:
            connect_kwargs = {
                "hostname": credentials.host,
                "port": credentials.port,
                "username": credentials.username,
                "timeout": 15,
                "look_for_keys": False,
                "allow_agent": False,
            }
            if credentials.private_key:
                connect_kwargs["pkey"] = paramiko.RSAKey.from_private_key_file(credentials.private_key)
            else:
                connect_kwargs["password"] = credentials.password

            client.connect(**connect_kwargs)

            cmd = f"ls -lh {NGINX_BACKUP_DIR}/html_*.tar.gz 2>/dev/null"
            if credentials.username != 'root':
                cmd = f"sudo {cmd}"
            stdin, stdout, stderr = client.exec_command(cmd)
            stdout.channel.recv_exit_status()
            output = stdout.read().decode().strip()

            backups = []
            if output:
                for line in output.split('\n'):
                    parts = line.split()
                    if len(parts) >= 9:
                        filename = parts[-1].split('/')[-1]
                        size = parts[4]
                        try:
                            date_str = filename.replace('html_', '').replace('.tar.gz', '')
                            dt = datetime.strptime(date_str, "%Y%m%d_%H%M%S")
                            created_at = dt.strftime("%Y-%m-%d %H:%M:%S")
                        except ValueError:
                            created_at = f"{parts[5]} {parts[6]} {parts[7]}"
                        backups.append({
                            "name": filename,
                            "size": size,
                            "created_at": created_at
                        })

            backups.sort(key=lambda x: x["name"], reverse=True)
            return backups

        except Exception as e:
            logger.error(f"Failed to get backups from {resource.ip_address}: {e}")
            raise
        finally:
            client.close()

    @staticmethod
    async def rollback(resource: Resource, backup_name: str, restart_keepalived: bool = False) -> DeployResult:
        """Rollback to a specific backup"""
        server_name = resource.ip_address or resource.name
        steps: List[DeployStepLog] = []

        def step_log(step: str, status: str, message: str = ""):
            steps.append(DeployStepLog(server=server_name, step=step, status=status, message=message))

        # Validate backup_name to prevent injection
        if not backup_name.startswith("html_") or not backup_name.endswith(".tar.gz"):
            return DeployResult(
                server=server_name, resource_id=resource.id,
                success=False, steps=steps, error="Invalid backup name"
            )
        if "/" in backup_name or ".." in backup_name:
            return DeployResult(
                server=server_name, resource_id=resource.id,
                success=False, steps=steps, error="Invalid backup name"
            )

        credentials = CredentialService.get_ssh_credentials(resource)
        client = create_secure_client()

        try:
            connect_kwargs = {
                "hostname": credentials.host,
                "port": credentials.port,
                "username": credentials.username,
                "timeout": 15,
                "look_for_keys": False,
                "allow_agent": False,
            }
            if credentials.private_key:
                connect_kwargs["pkey"] = paramiko.RSAKey.from_private_key_file(credentials.private_key)
            else:
                connect_kwargs["password"] = credentials.password

            client.connect(**connect_kwargs)
            step_log("SSH连接", "success")

            def execute(cmd: str) -> str:
                if credentials.username != 'root':
                    cmd = f"sudo {cmd}"
                stdin, stdout, stderr = client.exec_command(cmd)
                exit_status = stdout.channel.recv_exit_status()
                out = stdout.read().decode().strip()
                err = stderr.read().decode().strip()
                if exit_status != 0:
                    raise RuntimeError(f"Command failed (exit {exit_status}): {err or out}")
                return out

            # Check backup exists
            try:
                execute(f"test -f {NGINX_BACKUP_DIR}/{backup_name}")
            except Exception:
                return DeployResult(
                    server=server_name, resource_id=resource.id,
                    success=False, steps=steps, error=f"Backup {backup_name} not found"
                )

            # Clear and restore
            try:
                execute(f"rm -rf {NGINX_HTML_DIR}/*")
                execute(f"tar -xzf {NGINX_BACKUP_DIR}/{backup_name} -C {NGINX_BASE_DIR}")
                step_log("恢复备份代码", "success", backup_name)
            except Exception as e:
                step_log("恢复备份代码", "failed", str(e))
                return DeployResult(
                    server=server_name, resource_id=resource.id,
                    success=False, steps=steps, error="Restore failed"
                )

            # Restart Nginx
            try:
                execute(f"cd {NGINX_BASE_DIR} && docker-compose restart {NGINX_CONTAINER_NAME}")
                step_log("重启Nginx容器", "success")
            except Exception as e:
                step_log("重启Nginx容器", "failed", str(e))

            # Restart keepalived if requested
            if restart_keepalived:
                try:
                    execute("systemctl restart keepalived")
                    step_log("重启keepalived", "success")
                except Exception as e:
                    step_log("重启keepalived", "failed", str(e))

            return DeployResult(server=server_name, resource_id=resource.id, success=True, steps=steps)

        except Exception as e:
            return DeployResult(
                server=server_name, resource_id=resource.id,
                success=False, steps=steps, error=str(e)
            )
        finally:
            client.close()
