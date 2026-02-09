from sqlalchemy import Column, Integer, String, Float, JSON, DateTime, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class ResourceType(str, enum.Enum):
    """Resource type enumeration"""
    PHYSICAL = "physical"
    VIRTUAL = "virtual"
    CONTAINER = "container"
    CLOUD = "cloud"


class ResourceStatus(str, enum.Enum):
    """Resource status enumeration"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"
    OFFLINE = "offline"


class Resource(Base):
    """Resource model for CMDB"""
    __tablename__ = "resources"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False)
    type = Column(SQLEnum(ResourceType), nullable=False)
    status = Column(SQLEnum(ResourceStatus), default=ResourceStatus.ACTIVE)
    
    # Network info
    ip_address = Column(String(45))  # Support IPv6
    hostname = Column(String(255))
    
    # Hardware specs
    cpu_cores = Column(Integer)
    memory_gb = Column(Float)
    disk_gb = Column(Float)
    
    # System info
    os_type = Column(String(50))
    os_version = Column(String(50))
    
    # Metadata
    tags = Column(JSON, default=list)
    labels = Column(JSON, default=dict)
    description = Column(String(500))
    
    # Monitoring
    cpu_usage = Column(Float, default=0.0)
    memory_usage = Column(Float, default=0.0)
    disk_usage = Column(Float, default=0.0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_seen = Column(DateTime(timezone=True))
    
    # Relationships
    metrics = relationship("Metric", back_populates="resource", cascade="all, delete-orphan")
    
    # SSH Credentials (Encrypted)
    ssh_port = Column(Integer, default=22)
    ssh_username = Column(String(100), default="root")
    ssh_password_enc = Column(String(500), nullable=True) # Encrypted password
    ssh_private_key_enc = Column(String(2000), nullable=True) # Encrypted private key path or content
    
    def __repr__(self):
        return f"<Resource(name='{self.name}', type='{self.type}', status='{self.status}')>"
