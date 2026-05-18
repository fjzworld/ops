import re

with open('d:/Users/feng/Desktop/ai/Antigravity/ops-platform/backend/app/services/deploy_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Cachetools
content = content.replace('from functools import lru_cache', 'from functools import lru_cache\nimport cachetools')
content = content.replace('@lru_cache(maxsize=3)\ndef _get_deploy_config', '@cachetools.cached(cache=cachetools.TTLCache(maxsize=3, ttl=300))\ndef _get_deploy_config')

# 2. Path validation
content = content.replace(r"PATH_PATTERN = re.compile(r'^/[a-zA-Z0-9/_.\-]+$')", r"PATH_PATTERN = re.compile(r'^/[a-zA-Z0-9/_.\-@]+$')")

# 3. Concurrency Model for _deploy_single
# remove async
content = content.replace('    async def _deploy_single(', '    def _deploy_single(')

# fix deploy_to_servers
old_deploy_to_servers = '''    async def deploy_to_servers(
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
        results = await asyncio.gather(*tasks, return_exceptions=True)'''

new_deploy_to_servers = '''    async def deploy_to_servers(
        file_path: str,
        resources: List[Resource],
        deploy_type: str = "frontend",
        restart_keepalived: bool = False,
        restart_container: bool = True,
    ) -> List[DeployResult]:
        """Deploy code to multiple servers in parallel"""
        from fastapi.concurrency import run_in_threadpool
        tasks = [
            run_in_threadpool(
                DeployService._deploy_single,
                file_path, resource, deploy_type, restart_keepalived, restart_container
            )
            for resource in resources
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)'''

content = content.replace(old_deploy_to_servers, new_deploy_to_servers)

with open('d:/Users/feng/Desktop/ai/Antigravity/ops-platform/backend/app/services/deploy_service.py', 'w', encoding='utf-8') as f:
    f.write(content)
