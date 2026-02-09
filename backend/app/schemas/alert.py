from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime
from app.models.alert import AlertSeverity, AlertStatus


class AlertRuleBase(BaseModel):
    """Base alert rule schema"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    metric: str
    condition: str = Field(..., pattern="^(>|<|>=|<=|==|!=)$")
    threshold: float
    duration: int = Field(60, ge=0)
    severity: AlertSeverity = AlertSeverity.WARNING
    notification_channels: List[str] = []
    notification_template: Optional[str] = None


class AlertRuleCreate(AlertRuleBase):
    """Schema for creating an alert rule"""
    pass


class AlertRuleUpdate(BaseModel):
    """Schema for updating an alert rule"""
    description: Optional[str] = None
    threshold: Optional[float] = None
    duration: Optional[int] = None
    severity: Optional[AlertSeverity] = None
    enabled: Optional[bool] = None
    notification_channels: Optional[List[str]] = None


class AlertRuleInDB(AlertRuleBase):
    """Schema for alert rule in database"""
    id: int
    enabled: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class AlertBase(BaseModel):
    """Base alert schema"""
    rule_id: int
    resource_id: Optional[int] = None
    severity: AlertSeverity
    message: str
    current_value: float
    threshold_value: float


class AlertInDB(AlertBase):
    """Schema for alert in database"""
    id: int
    status: AlertStatus
    labels: Dict[str, str]
    annotations: Dict[str, str]
    fired_at: datetime
    resolved_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    
    class Config:
        from_attributes = True


class AlertAcknowledge(BaseModel):
    """Schema for acknowledging an alert"""
    acknowledged_by: str


class AlertStats(BaseModel):
    """Schema for alert statistics summary"""
    total: int
    firing: int
    acknowledged: int
    resolved: int
    by_severity: Dict[str, int]


class MessageResponse(BaseModel):
    """Generic message response schema"""
    message: str
