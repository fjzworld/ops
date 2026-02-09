from sqlalchemy import Column, Integer, String, Float, Boolean, JSON, DateTime, Enum as SQLEnum, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class AlertSeverity(str, enum.Enum):
    """Alert severity levels"""
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class AlertStatus(str, enum.Enum):
    """Alert status"""
    FIRING = "firing"
    RESOLVED = "resolved"
    ACKNOWLEDGED = "acknowledged"


class AlertRule(Base):
    """Alert rule configuration"""
    __tablename__ = "alert_rules"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(String(500))
    
    # Rule configuration
    metric = Column(String(100), nullable=False)  # cpu_usage, memory_usage, disk_usage
    condition = Column(String(10), nullable=False)  # >, <, >=, <=, ==, !=
    threshold = Column(Float, nullable=False)
    duration = Column(Integer, default=60)  # seconds
    
    # Alert settings
    severity = Column(SQLEnum(AlertSeverity), default=AlertSeverity.WARNING)
    enabled = Column(Boolean, default=True)
    
    # Notification
    notification_channels = Column(JSON, default=list)  # ["email", "dingtalk", "wechat"]
    notification_template = Column(String(1000))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<AlertRule(name='{self.name}', metric='{self.metric}')>"


class Alert(Base):
    """Alert instance"""
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    rule_id = Column(Integer, ForeignKey("alert_rules.id"), nullable=False)
    resource_id = Column(Integer, ForeignKey("resources.id"))
    
    # Alert details
    status = Column(SQLEnum(AlertStatus), default=AlertStatus.FIRING)
    severity = Column(SQLEnum(AlertSeverity), nullable=False)
    message = Column(String(1000))
    current_value = Column(Float)
    threshold_value = Column(Float)
    
    # Metadata
    labels = Column(JSON, default=dict)
    annotations = Column(JSON, default=dict)
    
    # Timestamps
    fired_at = Column(DateTime(timezone=True), server_default=func.now())
    resolved_at = Column(DateTime(timezone=True))
    acknowledged_at = Column(DateTime(timezone=True))
    acknowledged_by = Column(String(100))
    
    def __repr__(self):
        return f"<Alert(id={self.id}, status='{self.status}', severity='{self.severity}')>"
