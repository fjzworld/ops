"""
Permission decorators for role-based access control
"""
from functools import wraps
from fastapi import HTTPException, status, Depends
from typing import List, Callable
from app.models.user import User
from app.api.v1.auth import get_current_active_user


def require_roles(allowed_roles: List[str]) -> Callable:
    """
    Decorator to restrict endpoint access to specific user roles.
    
    Args:
        allowed_roles: List of allowed role names (e.g., ['admin', 'operator'])
    
    Usage:
        @router.post("/rules")
        @require_roles(['admin', 'operator'])
        async def create_rule(...):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, current_user: User = Depends(get_current_active_user), **kwargs):
            if current_user.role not in allowed_roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Not enough permissions. Required roles: {', '.join(allowed_roles)}"
                )
            return await func(*args, current_user=current_user, **kwargs)
        return wrapper
    return decorator


# Predefined role decorators for common use cases
require_admin = require_roles(['admin'])
require_admin_or_operator = require_roles(['admin', 'operator'])
require_any_authenticated = require_roles(['admin', 'operator', 'user', 'readonly'])
