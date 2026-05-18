import re

with open('d:/Users/feng/Desktop/ai/Antigravity/ops-platform/backend/app/core/config.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = re.sub(
    r'raise ValueError\([^)]+\)',
    r'''import warnings; warnings.warn("SECURITY WARNING: Missing or weak SECRET_KEY in production. Please configure a strong 32-byte key.", UserWarning)''',
    content
)

with open('d:/Users/feng/Desktop/ai/Antigravity/ops-platform/backend/app/core/config.py', 'w', encoding='utf-8') as f:
    f.write(content)
