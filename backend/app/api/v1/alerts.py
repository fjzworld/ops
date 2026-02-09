from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from app.core.database import get_db
from app.models.user import User
from app.models.alert import Alert, AlertRule, AlertStatus, AlertSeverity
from app.schemas.alert import (
    AlertRuleCreate, AlertRuleUpdate, AlertRuleInDB,
    AlertInDB, AlertAcknowledge, AlertStats, MessageResponse
)
from app.api.v1.auth import get_current_active_user

router = APIRouter()


# Alert Rules endpoints
@router.get("/rules", response_model=List[AlertRuleInDB])
async def list_alert_rules(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    enabled: Optional[bool] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List all alert rules"""
    query = db.query(AlertRule)
    
    if enabled is not None:
        query = query.filter(AlertRule.enabled == enabled)
    
    rules = query.offset(skip).limit(limit).all()
    return rules


@router.post("/rules", response_model=AlertRuleInDB, status_code=status.HTTP_201_CREATED)
async def create_alert_rule(
    rule_data: AlertRuleCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new alert rule"""
    if current_user.role not in ["admin", "operator"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Check if rule name already exists
    if db.query(AlertRule).filter(AlertRule.name == rule_data.name).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Alert rule name already exists"
        )
    
    db_rule = AlertRule(**rule_data.dict())
    db.add(db_rule)
    db.commit()
    db.refresh(db_rule)
    
    return db_rule


@router.put("/rules/{rule_id}", response_model=AlertRuleInDB)
async def update_alert_rule(
    rule_id: int,
    rule_update: AlertRuleUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update alert rule"""
    if current_user.role not in ["admin", "operator"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    rule = db.query(AlertRule).filter(AlertRule.id == rule_id).first()
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert rule not found"
        )
    
    update_data = rule_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(rule, field, value)
    
    db.commit()
    db.refresh(rule)
    
    return rule


@router.delete("/rules/{rule_id}", response_model=MessageResponse)
async def delete_alert_rule(
    rule_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete alert rule"""
    if current_user.role not in ["admin", "operator"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    rule = db.query(AlertRule).filter(AlertRule.id == rule_id).first()
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert rule not found"
        )
    
    db.delete(rule)
    db.commit()
    
    return {"message": "Alert rule deleted successfully"}


# Alerts endpoints
@router.get("/", response_model=List[AlertInDB])
async def list_alerts(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[AlertStatus] = None,
    severity: Optional[AlertSeverity] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List all alerts"""
    query = db.query(Alert)
    
    if status:
        query = query.filter(Alert.status == status)
    
    if severity:
        query = query.filter(Alert.severity == severity)
    
    alerts = query.order_by(Alert.fired_at.desc()).offset(skip).limit(limit).all()
    return alerts


@router.get("/{alert_id}", response_model=AlertInDB)
async def get_alert(
    alert_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get alert by ID"""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )
    
    return alert


@router.post("/{alert_id}/acknowledge", response_model=MessageResponse)
async def acknowledge_alert(
    alert_id: int,
    ack_data: AlertAcknowledge,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Acknowledge an alert"""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )
    
    alert.status = AlertStatus.ACKNOWLEDGED
    alert.acknowledged_at = datetime.utcnow()
    alert.acknowledged_by = ack_data.acknowledged_by
    
    db.commit()
    
    return {"message": "Alert acknowledged successfully"}


@router.post("/{alert_id}/resolve", response_model=MessageResponse)
async def resolve_alert(
    alert_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Resolve an alert"""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )
    
    alert.status = AlertStatus.RESOLVED
    alert.resolved_at = datetime.utcnow()
    
    db.commit()
    
    return {"message": "Alert resolved successfully"}


@router.get("/stats/summary", response_model=AlertStats)
async def get_alert_stats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get alert statistics summary"""
    total = db.query(Alert).count()
    firing = db.query(Alert).filter(Alert.status == AlertStatus.FIRING).count()
    acknowledged = db.query(Alert).filter(Alert.status == AlertStatus.ACKNOWLEDGED).count()
    resolved = db.query(Alert).filter(Alert.status == AlertStatus.RESOLVED).count()
    
    by_severity = {}
    for severity in AlertSeverity:
        count = db.query(Alert).filter(Alert.severity == severity).count()
        by_severity[severity.value] = count
    
    return {
        "total": total,
        "firing": firing,
        "acknowledged": acknowledged,
        "resolved": resolved,
        "by_severity": by_severity
    }
