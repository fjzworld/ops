import os
import secrets
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from typing import Optional, List


def generate_secure_key() -> str:
    """Generate a cryptographically secure secret key"""
    return secrets.token_urlsafe(32)


class Settings(BaseSettings):
    """Application settings with security validation"""
    
    # Application
    APP_NAME: str = "OPS Platform"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # Database
    DATABASE_URL: str = Field(default="postgresql://opsuser:opspass@localhost:5432/opsplatform")
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Security - SECRET_KEY must be provided via environment variable in production
    SECRET_KEY: str = Field(
        default_factory=generate_secure_key,
        min_length=32,
        description="Secret key for JWT signing. Must be set via environment variable in production."
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Encryption key for sensitive data (SSH credentials, etc.)
    ENCRYPTION_KEY: Optional[str] = Field(
        default=None,
        description="32-byte base64-encoded encryption key. Auto-generated from SECRET_KEY if not provided."
    )
    
    # CORS
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000,http://localhost"
    
    # External URL for agents to connect back to the API
    # This should be set to the external IP/domain of the backend (e.g. http://192.168.1.100:8000/api/v1)
    EXTERNAL_API_URL: str = "http://localhost:8000/api/v1"

    # Loki
    LOKI_URL: str = "http://loki:3100"

    # Prometheus
    PROMETHEUS_URL: str = "http://prometheus:9090"

    # External Loki URL for remote Promtail agents to push logs
    # Must be reachable from target servers (e.g. http://192.168.1.100:3100)
    LOKI_EXTERNAL_URL: str = ""

    @property
    def cors_origins_list(self) -> List[str]:
        """Convert CORS_ORIGINS string to list"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(',')]
    
    @property
    def ASYNC_DATABASE_URL(self) -> str:
        """Get async database URL"""
        url = self.DATABASE_URL
        if url and url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url
    
    # Pagination
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100
    
    @field_validator('SECRET_KEY')
    @classmethod
    def validate_secret_key(cls, v: str, info) -> str:
        """Validate that SECRET_KEY is properly set in production"""
        # Check if running in production (DEBUG=False)
        debug = info.data.get('DEBUG', True)
        
        if not debug:
            # In production, SECRET_KEY must come from environment
            if 'SECRET_KEY' not in os.environ:
                raise ValueError(
                    "SECRET_KEY must be explicitly set via environment variable in production mode. "
                    "Do not use default or generated keys in production."
                )
            
            # Validate key strength
            if len(v) < 32:
                raise ValueError("SECRET_KEY must be at least 32 characters long in production")
            
            # Check for weak default keys
            weak_keys = ['your-secret', 'change-this', 'secret-key', 'default']
            if any(weak in v.lower() for weak in weak_keys):
                raise ValueError(
                    "SECRET_KEY appears to be a weak/default value. "
                    "Please generate a strong random key for production."
                )
        
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        # Validate on initialization
        validate_assignment = True


# Initialize settings
settings = Settings()

# Warn if using generated key in non-production
if settings.DEBUG and 'SECRET_KEY' not in os.environ:
    import warnings
    warnings.warn(
        "Using auto-generated SECRET_KEY. This is fine for development, "
        "but you should set a persistent SECRET_KEY in production.",
        UserWarning
    )
