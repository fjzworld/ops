import re

with open('d:/Users/feng/Desktop/ai/Antigravity/ops-platform/backend/app/services/docker_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add re to imports
content = content.replace('import json\nimport logging', 'import json\nimport logging\nimport re')

# Add validation method
validation_method = '''    def _validate_container_id(self, container_id: str) -> None:
        """Validate container ID to prevent command injection"""
        if not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9_.\\\\-]{0,127}$", container_id):
            raise ValueError(f"Invalid container ID format: {container_id}")

    def start_container(self, container_id: str) -> bool:'''

content = content.replace('    def start_container(self, container_id: str) -> bool:', validation_method)

# Inject validation into methods
content = content.replace('        """Start a stopped container"""\n        try:', '        """Start a stopped container"""\n        self._validate_container_id(container_id)\n        try:')
content = content.replace('        """Stop a running container"""\n        try:', '        """Stop a running container"""\n        self._validate_container_id(container_id)\n        try:')
content = content.replace('        """Restart a container"""\n        try:', '        """Restart a container"""\n        self._validate_container_id(container_id)\n        try:')
content = content.replace('        """Remove a container (force)"""\n        try:', '        """Remove a container (force)"""\n        self._validate_container_id(container_id)\n        try:')

# get_logs signature includes tail, wait, no, the docstring is different
content = content.replace('        """\n        try:\n            self.detector.connect()', '        """\n        self._validate_container_id(container_id)\n        try:\n            self.detector.connect()')

with open('d:/Users/feng/Desktop/ai/Antigravity/ops-platform/backend/app/services/docker_service.py', 'w', encoding='utf-8') as f:
    f.write(content)
