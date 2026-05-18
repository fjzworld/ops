import re

with open('d:/Users/feng/Desktop/ai/Antigravity/ops-platform/backend/app/services/deploy_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

# get_backups
old_get_backups = '''    @staticmethod
    async def get_backups(resource: Resource, deploy_type: str = "frontend") -> List[dict]:
        """Get backup list from remote server"""'''

new_get_backups = '''    @staticmethod
    def _get_backups_sync(resource: Resource, deploy_type: str = "frontend") -> List[dict]:
        """Get backup list from remote server (sync)"""'''

new_async_get_backups = '''    @staticmethod
    async def get_backups(resource: Resource, deploy_type: str = "frontend") -> List[dict]:
        """Get backup list from remote server"""
        from fastapi.concurrency import run_in_threadpool
        return await run_in_threadpool(DeployService._get_backups_sync, resource, deploy_type)

    @staticmethod
    def _get_backups_sync(resource: Resource, deploy_type: str = "frontend") -> List[dict]:
        """Get backup list from remote server (sync)"""'''

content = content.replace(old_get_backups, new_async_get_backups)

# rollback
old_rollback = '''    @staticmethod
    async def rollback(
        resource: Resource,
        backup_name: str,
        deploy_type: str = "frontend",
        restart_keepalived: bool = False,
        restart_container: bool = True,
    ) -> DeployResult:
        """Rollback to a specific backup"""'''

new_async_rollback = '''    @staticmethod
    async def rollback(
        resource: Resource,
        backup_name: str,
        deploy_type: str = "frontend",
        restart_keepalived: bool = False,
        restart_container: bool = True,
    ) -> DeployResult:
        """Rollback to a specific backup"""
        from fastapi.concurrency import run_in_threadpool
        return await run_in_threadpool(
            DeployService._rollback_sync,
            resource, backup_name, deploy_type, restart_keepalived, restart_container
        )

    @staticmethod
    def _rollback_sync(
        resource: Resource,
        backup_name: str,
        deploy_type: str = "frontend",
        restart_keepalived: bool = False,
        restart_container: bool = True,
    ) -> DeployResult:
        """Rollback to a specific backup (sync)"""'''

content = content.replace(old_rollback, new_async_rollback)

with open('d:/Users/feng/Desktop/ai/Antigravity/ops-platform/backend/app/services/deploy_service.py', 'w', encoding='utf-8') as f:
    f.write(content)
