import logging
import json
from app.models.audit_log import AuditLog
from app.core.database import SessionLocal
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

def log_audit_action(
    db: Any,
    user_id: Optional[int],
    resource_type: str,
    resource_id: str,
    action: str,
    details: Dict[str, Any] = None,
    ip_address: str = None
):
    """
    Log an audit action to the database.
    Can be used synchronously within a request or asynchronously from a task.
    """
    try:
        if details is None:
            details = {}
            
        # Serialize details if it contains non-serializable objects (basic check)
        # SQLAlchemy JSON type handles dicts, but let's ensure safety for custom objects
        
        audit_entry = AuditLog(
            user_id=user_id,
            resource_type=resource_type,
            resource_id=str(resource_id),
            action=action,
            details=details,
            ip_address=ip_address
        )
        
        db.add(audit_entry)
        # If db is a session from a request, we might not want to commit immediately
        # to ensure atomicity with the main transaction. 
        # But for audit logs, we often want them even if main transaction fails?
        # Usually: Audit success actions only. 
        # We'll let the caller handle commit if it's the main session, 
        # or we assume this is part of the main flow.
        # But to be safe and simple: just add, let caller commit.
        
    except Exception as e:
        logger.error(f"Failed to create audit log: {e}")
