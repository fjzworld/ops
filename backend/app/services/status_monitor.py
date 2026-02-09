import asyncio
import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.resource import Resource, ResourceStatus
from app.core.monitoring import clear_metrics

logger = logging.getLogger(__name__)

async def check_resource_status():
    """
    Background task to check resource status.
    If a resource hasn't been seen for > 90 seconds, mark it as OFFLINE.
    """
    logger.info("Starting resource status monitor...")
    
    while True:
        try:
            db = SessionLocal()
            try:
                # Find active resources that haven't been seen recently
                threshold = datetime.utcnow() - timedelta(seconds=90)
                
                # Active resources with old last_seen
                stale_resources = db.query(Resource).filter(
                    Resource.status == ResourceStatus.ACTIVE,
                    Resource.last_seen < threshold
                ).all()
                
                for res in stale_resources:
                    logger.warning(f"Resource {res.name} ({res.ip_address}) timed out. Marking OFFLINE.")
                    
                    # Update DB status
                    res.status = ResourceStatus.OFFLINE
                    res.cpu_usage = 0.0
                    res.memory_usage = 0.0
                    res.disk_usage = 0.0
                    
                    # Clear Prometheus metrics (avoid stale data)
                    clear_metrics(str(res.id), res.name, res.ip_address)
                
                if stale_resources:
                    db.commit()
                    
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error in status monitor: {e}")
            
        # Check every 30 seconds
        await asyncio.sleep(30)

def start_status_monitor():
    """Start the background monitoring task"""
    asyncio.create_task(check_resource_status())
