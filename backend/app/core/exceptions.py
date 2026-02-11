from typing import Any, Dict, Optional
from fastapi import status

class AppException(Exception):
    """Base exception for application"""
    def __init__(
        self,
        status_code: int,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        self.status_code = status_code
        self.message = message
        self.details = details or {}
        super().__init__(message)

class NotFoundException(AppException):
    def __init__(self, message: str = "Resource not found", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            message=message,
            details=details
        )

class BadRequestException(AppException):
    def __init__(self, message: str = "Bad request", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=message,
            details=details
        )

class UnauthorizedException(AppException):
    def __init__(self, message: str = "Unauthorized", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            message=message,
            details=details
        )

class PermissionDeniedException(AppException):
    def __init__(self, message: str = "Permission denied", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            message=message,
            details=details
        )

class InternalServerError(AppException):
    def __init__(self, message: str = "Internal server error", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=message,
            details=details
        )
