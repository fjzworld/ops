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
        if filename.endswith(".tar.gz") or filename.endswith(".tgz"):
            ext = ".tar.gz"
        elif filename.endswith(".zip"):
            ext = ".zip"
        else:
            raise ValueError("Only .zip and .tar.gz files are supported")

        save_path = UPLOAD_DIR / f"{file_id}{ext}"
        save_path.write_bytes(file_content)
        return file_id, str(save_path)

    @staticmethod
    def validate_package(
        file_path: str, deploy_type: str = "frontend"
    ) -> Tuple[bool, str]:
        """Validate that the package contains expected files based on deploy_type"""
        try:
            if file_path.endswith(".zip"):
                with zipfile.ZipFile(file_path, "r") as zf:
                    names = zf.namelist()
            elif file_path.endswith(".tar.gz") or file_path.endswith(".tgz"):
                with tarfile.open(file_path, "r:gz") as tf:
                    names = tf.getnames()
            else:
                return False, "Unsupported file format"

            if deploy_type == "frontend":
                has_index = any(n.endswith("index.html") for n in names)
                if not has_index:
                    return False, "Frontend package does not contain index.html"

            # For backend and algorithm, we just accept the archive as is
            return True, "Package is valid"
        except Exception as e:
            return False, f"Failed to validate package: {str(e)}"

    @staticmethod
    def get_upload_path(file_id: str) -> Optional[str]:
        """Find uploaded file by file_id"""
        for ext in [".zip", ".tar.gz"]:
            path = UPLOAD_DIR / f"{file_id}{ext}"
            if path.exists():
                return str(path)
        return None

    @staticmethod
    def cleanup_upload(file_id: str):
        """Remove uploaded file"""
        for ext in [".zip", ".tar.gz"]:
            path = UPLOAD_DIR / f"{file_id}{ext}"
            if path.exists():
                path.unlink()

    @staticmethod
    async def deploy_to_servers(
        file_path: str,
        resources: List[Resource],
        deploy_type: str = "frontend",
        restart_keepalived: bool = False,
        restart_container: bool = True,
    ) -> List[DeployResult]:
        """Deploy code to multiple servers in parallel"""
        tasks = [
            DeployService._deploy_single(
                file_path, resource, deploy_type, restart_keepalived, restart_container
            )
            for resource in resources
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        deploy_results: List[DeployResult] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                deploy_results.append(
                    DeployResult(
                        server=resources[i].ip_address or resources[i].name,
                        resource_id=resources[i].id,
                        success=False,
                        error=str(result),
                    )
                )
            else:
                deploy_results.append(result)

        return deploy_results

    @staticmethod
    async def _deploy_single(
        file_path: str,
        resource: Resource,
        deploy_type: str,
        restart_keepalived: bool,
        restart_container: bool,
    ) -> DeployResult:
        """Deploy to a single server via SSH"""
        server_name = resource.ip_address or resource.name
        steps: List[DeployStepLog] = []

        def step_log(step: str, status: str, message: str = ""):
            steps.append(
                DeployStepLog(
                    server=server_name, step=step, status=status, message=message
                )
            )
            if status == "failed":
                logger.error(f"[Deploy:{server_name}] {step}: {message}")
            else:
                logger.info(f"[Deploy:{server_name}] {step}: {status} {message}")

        # Define paths based on deploy_type
        if deploy_type == "frontend":
            target_dir = NGINX_HTML_DIR
            target_parent = NGINX_BASE_DIR
            target_folder = "html"
            backup_dir = NGINX_BACKUP_DIR
            backup_prefix = "html"
            restart_commands = [f"docker restart {NGINX_CONTAINER_NAME}"]
        else:
            # For backend/algorithm deployments - these should be configured per resource
            # Using defaults for now
            target_dir = f"/opt/{deploy_type}"
            target_parent = "/opt"
            target_folder = deploy_type
            backup_dir = f"/opt/backup/{deploy_type}"
            backup_prefix = deploy_type
            restart_commands = [f"systemctl restart {deploy_type}"]

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
                connect_kwargs["pkey"] = paramiko.RSAKey.from_private_key_file(
                    credentials.private_key
                )
            else:
                connect_kwargs["password"] = credentials.password

            client.connect(**connect_kwargs)
            step_log("SSH连接", "success")

            def execute(cmd: str) -> str:
                if credentials.username != "root":
                    cmd = f"sudo {cmd}"
                stdin, stdout, stderr = client.exec_command(cmd)
                exit_status = stdout.channel.recv_exit_status()
                out = stdout.read().decode().strip()
                err = stderr.read().decode().strip()
                if exit_status != 0:
                    raise RuntimeError(
                        f"Command failed (exit {exit_status}): {err or out}"
                    )
                return out

            # 1. Create backup directory
            execute(f"mkdir -p {backup_dir}")

            # 2. Backup current code
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{backup_prefix}_{timestamp}.tar.gz"
            try:
                execute(
                    f"tar -czf {backup_dir}/{backup_name} -C {target_parent} {target_folder}/"
                )
                step_log("备份当前代码", "success", backup_name)
            except Exception as e:
                step_log("备份当前代码", "failed", str(e))
                # Allow continuing if the target directory doesn't exist yet (first deploy)

            # 3. Clean old backups (older than 3 days)
            try:
                execute(
                    f"find {backup_dir} -name '{backup_prefix}_*.tar.gz' -mtime +3 -delete"
                )
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
                    server=server_name,
                    resource_id=resource.id,
                    success=False,
                    steps=steps,
                    error="Upload failed",
                )

            # 5. Clear target dir and extract
            try:
                execute(f"mkdir -p {target_dir}")
                execute(f"rm -rf {target_dir}/*")
                extract_id = uuid.uuid4().hex[:8]
                extract_dir = f"/tmp/deploy_extract_{extract_id}"

                if file_path.endswith(".zip"):
                    execute(f"unzip -o {remote_tmp}.pkg -d {extract_dir}")
                else:
                    execute(f"mkdir -p {extract_dir}")
                    execute(f"tar -xzf {remote_tmp}.pkg -C {extract_dir}")

                if deploy_type == "frontend":
                    check = execute(
                        f"if [ -f {extract_dir}/index.html ]; then echo 'root'; "
                        f"else ls -d {extract_dir}/*/index.html 2>/dev/null | head -1; fi"
                    )
                    if check == "root":
                        execute(f"cp -a {extract_dir}/* {target_dir}/")
                    else:
                        subdir = check.rsplit("/index.html", 1)[0]
                        execute(f"cp -a {subdir}/* {target_dir}/")
                else:
                    # For backend and algorithm, copy all extracted files into the target_dir
                    # Check if there's only one root directory in the archive
                    check_dirs = execute(f"ls -A {extract_dir} | wc -l").strip()
                    if check_dirs == "1":
                        only_item = execute(f"ls -A {extract_dir}").strip()
                        if (
                            execute(
                                f"if [ -d {extract_dir}/{only_item} ]; then echo 'DIR'; else echo 'FILE'; fi"
                            )
                            == "DIR"
                        ):
                            execute(f"cp -a {extract_dir}/{only_item}/* {target_dir}/")
                        else:
                            execute(f"cp -a {extract_dir}/* {target_dir}/")
                    else:
                        execute(f"cp -a {extract_dir}/* {target_dir}/")

                execute(f"rm -rf {extract_dir} {remote_tmp}.pkg")
                step_log("解压并替换代码", "success")
            except Exception as e:
                step_log("解压并替换代码", "failed", str(e))
                try:
                    execute(f"rm -rf {target_dir}/*")
                    execute(f"tar -xzf {backup_dir}/{backup_name} -C {target_parent}")
                    step_log("自动回滚", "success", f"已回滚到 {backup_name}")
                except Exception:
                    step_log("自动回滚", "failed", "回滚也失败了，请手动处理")
                return DeployResult(
                    server=server_name,
                    resource_id=resource.id,
                    success=False,
                    steps=steps,
                    error="Extract failed",
                )

            # 6. Restart Container(s)
            if restart_container:
                for cmd in restart_commands:
                    try:
                        execute(cmd)
                        step_log("重启容器", "success", cmd)
                    except Exception as e:
                        step_log("重启容器", "failed", str(e))
                        return DeployResult(
                            server=server_name,
                            resource_id=resource.id,
                            success=False,
                            steps=steps,
                            error="Container restart failed",
                        )
            else:
                step_log("重启容器", "success", "用户选择跳过重启")

            # 7. Restart keepalived (only if frontend HA)
            if restart_keepalived and deploy_type == "frontend":
                try:
                    execute("systemctl restart keepalived")
                    step_log("重启keepalived", "success")
                except Exception as e:
                    step_log("重启keepalived", "failed", str(e))
            return DeployResult(
                server=server_name, resource_id=resource.id, success=True, steps=steps
            )

        except Exception as e:
            step_log("部署异常", "failed", str(e))
            return DeployResult(
                server=server_name,
                resource_id=resource.id,
                success=False,
                steps=steps,
                error=str(e),
            )
        finally:
            client.close()

    @staticmethod
    async def get_backups(resource: Resource, deploy_type: str = "frontend") -> List[dict]:
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
                connect_kwargs["pkey"] = paramiko.RSAKey.from_private_key_file(
                    credentials.private_key
                )
            else:
                connect_kwargs["password"] = credentials.password

            client.connect(**connect_kwargs)

            if deploy_type == "frontend":
                backup_dir = NGINX_BACKUP_DIR
                backup_prefix = "html"
            else:
                backup_dir = f"/opt/backup/{deploy_type}"
                backup_prefix = deploy_type

            cmd = f"ls -lh {backup_dir}/{backup_prefix}_*.tar.gz 2>/dev/null"
            if credentials.username != "root":
                cmd = f"sudo {cmd}"
            stdin, stdout, stderr = client.exec_command(cmd)
            stdout.channel.recv_exit_status()
            output = stdout.read().decode().strip()

            backups = []
            if output:
                for line in output.split("\n"):
                    parts = line.split()
                    if len(parts) >= 9:
                        filename = parts[-1].split("/")[-1]
                        size = parts[4]
                        try:
                            date_str = filename.replace(f"{backup_prefix}_", "").replace(
                                ".tar.gz", ""
                            )
                            dt = datetime.strptime(date_str, "%Y%m%d_%H%M%S")
                            created_at = dt.strftime("%Y-%m-%d %H:%M:%S")
                        except ValueError:
                            created_at = f"{parts[5]} {parts[6]} {parts[7]}"
                        backups.append(
                            {"name": filename, "size": size, "created_at": created_at}
                        )

            backups.sort(key=lambda x: x["name"], reverse=True)
            return backups

        except Exception as e:
            logger.error(f"Failed to get backups from {resource.ip_address}: {e}")
            raise
        finally:
            client.close()

    @staticmethod
    async def rollback(
        resource: Resource,
        backup_name: str,
        deploy_type: str = "frontend",
        restart_keepalived: bool = False,
        restart_container: bool = True,
    ) -> DeployResult:
        """Rollback to a specific backup"""
        server_name = resource.ip_address or resource.name
        steps: List[DeployStepLog] = []

        def step_log(step: str, status: str, message: str = ""):
            steps.append(
                DeployStepLog(
                    server=server_name, step=step, status=status, message=message
                )
            )

        # Define paths based on deploy_type
        if deploy_type == "frontend":
            target_dir = NGINX_HTML_DIR
            target_parent = NGINX_BASE_DIR
            backup_dir = NGINX_BACKUP_DIR
            restart_commands = [f"docker restart {NGINX_CONTAINER_NAME}"]
        else:
            target_dir = f"/opt/{deploy_type}"
            target_parent = "/opt"
            backup_dir = f"/opt/backup/{deploy_type}"
            restart_commands = [f"systemctl restart {deploy_type}"]

        # Validate backup_name to prevent injection
        expected_prefix = "html" if deploy_type == "frontend" else deploy_type
        if not backup_name.startswith(f"{expected_prefix}_") or not backup_name.endswith(
            ".tar.gz"
        ):
            return DeployResult(
                server=server_name,
                resource_id=resource.id,
                success=False,
                steps=steps,
                error="Invalid backup name",
            )
        if "/" in backup_name or ".." in backup_name:
            return DeployResult(
                server=server_name,
                resource_id=resource.id,
                success=False,
                steps=steps,
                error="Invalid backup name",
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
                connect_kwargs["pkey"] = paramiko.RSAKey.from_private_key_file(
                    credentials.private_key
                )
            else:
                connect_kwargs["password"] = credentials.password

            client.connect(**connect_kwargs)
            step_log("SSH连接", "success")

            def execute(cmd: str) -> str:
                if credentials.username != "root":
                    cmd = f"sudo {cmd}"
                stdin, stdout, stderr = client.exec_command(cmd)
                exit_status = stdout.channel.recv_exit_status()
                out = stdout.read().decode().strip()
                err = stderr.read().decode().strip()
                if exit_status != 0:
                    raise RuntimeError(
                        f"Command failed (exit {exit_status}): {err or out}"
                    )
                return out

            # Check backup exists
            try:
                execute(f"test -f {backup_dir}/{backup_name}")
            except Exception:
                return DeployResult(
                    server=server_name,
                    resource_id=resource.id,
                    success=False,
                    steps=steps,
                    error=f"Backup {backup_name} not found",
                )

            # Rollback
            try:
                execute(f"rm -rf {target_dir}/*")
                execute(f"tar -xzf {backup_dir}/{backup_name} -C {target_parent}")
                step_log("恢复备份", "success", backup_name)
            except Exception as e:
                step_log("恢复备份", "failed", str(e))
                return DeployResult(
                    server=server_name,
                    resource_id=resource.id,
                    success=False,
                    steps=steps,
                    error="Rollback failed",
                )

            # Restart Container(s)
            if restart_container:
                for cmd in restart_commands:
                    try:
                        execute(cmd)
                        step_log("重启容器", "success", cmd)
                    except Exception as e:
                        step_log("重启容器", "failed", str(e))
                        return DeployResult(
                            server=server_name,
                            resource_id=resource.id,
                            success=False,
                            steps=steps,
                            error="Container restart failed",
                        )
            else:
                step_log("重启容器", "success", "用户选择跳过重启")

            # Restart keepalived
            if restart_keepalived and deploy_type == "frontend":
                try:
                    execute("systemctl restart keepalived")
                    step_log("重启keepalived", "success")
                except Exception as e:
                    step_log("重启keepalived", "failed", str(e))
            return DeployResult(
                server=server_name, resource_id=resource.id, success=True, steps=steps
            )

        except Exception as e:
            return DeployResult(
                server=server_name,
                resource_id=resource.id,
                success=False,
                steps=steps,
                error=str(e),
            )
        finally:
            client.close()
