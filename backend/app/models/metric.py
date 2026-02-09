"""
Metric model for storing time-series monitoring data
"""
from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, String, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class Metric(Base):
    """Time-series metrics from monitored resources"""
    
    __tablename__ = "metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    resource_id = Column(Integer, ForeignKey("resources.id"), nullable=False, index=True)
    
    # System metrics
    cpu_usage = Column(Float, nullable=False)
    memory_usage = Column(Float, nullable=False)
    disk_usage = Column(Float, nullable=False)
    
    # Network metrics
    network_in = Column(Float, default=0.0)  # MB/s
    network_out = Column(Float, default=0.0)  # MB/s
    
    # Additional metrics (JSON for flexibility)
    extra_data = Column(JSON, default={})
    
    # Timestamp
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationship
    resource = relationship("Resource", back_populates="metrics")


class ProcessMetric(Base):
    """Top process metrics"""
    
    __tablename__ = "process_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    resource_id = Column(Integer, ForeignKey("resources.id"), nullable=False, index=True)
    
    # Process info
    process_name = Column(String(255), nullable=False)
    process_pid = Column(Integer, nullable=False)
    cpu_percent = Column(Float, default=0.0)
    memory_percent = Column(Float, default=0.0)
    
    # Timestamp
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationship
    resource = relationship("Resource")
