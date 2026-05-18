import re

with open('d:/Users/feng/Desktop/ai/Antigravity/ops-platform/backend/app/api/v1/auth.py', 'r', encoding='utf-8') as f:
    content = f.read()

new_logic = '''    from sqlalchemy import func
    from app.core.exceptions import PermissionDeniedException

    user_count_result = await db.execute(select(func.count()).select_from(User))
    user_count = user_count_result.scalar()

    if user_count > 0:
        # Require admin privileges if users already exist
        try:
            token = _extract_token(request, None)
            payload = decode_access_token(token)
            username = payload.get("sub")
            admin_check = await db.execute(select(User).filter(User.username == username, User.role == "admin"))
            if not admin_check.scalars().first():
                raise PermissionDeniedException(message="Registration is restricted to admin only")
        except Exception:
            raise PermissionDeniedException(message="Registration is restricted to admin only")

    # Check if username exists'''

content = content.replace('    # Check if username exists', new_logic)

with open('d:/Users/feng/Desktop/ai/Antigravity/ops-platform/backend/app/api/v1/auth.py', 'w', encoding='utf-8') as f:
    f.write(content)
