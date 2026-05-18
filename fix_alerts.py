import re

with open('d:/Users/feng/Desktop/ai/Antigravity/ops-platform/backend/app/api/v1/alerts.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Imports
content = content.replace('from sqlalchemy.orm import Session', 'from sqlalchemy.ext.asyncio import AsyncSession\nfrom sqlalchemy import select, func')
content = content.replace('from app.core.database import get_db', 'from app.core.database import get_async_db')
content = content.replace('db: Session = Depends(get_db)', 'db: AsyncSession = Depends(get_async_db)')

# DB operations
content = content.replace('db.commit()', 'await db.commit()')
content = content.replace('db.refresh(', 'await db.refresh(')
content = content.replace('db.delete(', 'await db.delete(')

# list_alert_rules
content = content.replace('query = db.query(AlertRule)', 'query = select(AlertRule)')
content = content.replace('rules = query.offset(skip).limit(limit).all()', 'result = await db.execute(query.offset(skip).limit(limit))\n    rules = result.scalars().all()')

# create_alert_rule
content = content.replace('if db.query(AlertRule).filter(AlertRule.name == rule_data.name).first():', 'result = await db.execute(select(AlertRule).filter(AlertRule.name == rule_data.name))\n    if result.scalars().first():')

# update_alert_rule
content = content.replace('rule = db.query(AlertRule).filter(AlertRule.id == rule_id).first()', 'result = await db.execute(select(AlertRule).filter(AlertRule.id == rule_id))\n    rule = result.scalars().first()')

# list_alerts
content = content.replace('query = db.query(Alert)', 'query = select(Alert)')
content = content.replace('alerts = query.order_by(Alert.fired_at.desc()).offset(skip).limit(limit).all()', 'result = await db.execute(query.order_by(Alert.fired_at.desc()).offset(skip).limit(limit))\n    alerts = result.scalars().all()')

# get_alert
content = content.replace('alert = db.query(Alert).filter(Alert.id == alert_id).first()', 'result = await db.execute(select(Alert).filter(Alert.id == alert_id))\n    alert = result.scalars().first()')

# get_alert_stats
old_stats = '''    total = db.query(Alert).count()
    firing = db.query(Alert).filter(Alert.status == AlertStatus.FIRING).count()
    acknowledged = (
        db.query(Alert).filter(Alert.status == AlertStatus.ACKNOWLEDGED).count()
    )
    resolved = db.query(Alert).filter(Alert.status == AlertStatus.RESOLVED).count()

    by_severity = {}
    for severity in AlertSeverity:
        count = db.query(Alert).filter(Alert.severity == severity).count()
        by_severity[severity.value] = count'''

new_stats = '''    total = (await db.execute(select(func.count()).select_from(Alert))).scalar()
    firing = (await db.execute(select(func.count()).select_from(Alert).filter(Alert.status == AlertStatus.FIRING))).scalar()
    acknowledged = (
        await db.execute(select(func.count()).select_from(Alert).filter(Alert.status == AlertStatus.ACKNOWLEDGED))
    ).scalar()
    resolved = (await db.execute(select(func.count()).select_from(Alert).filter(Alert.status == AlertStatus.RESOLVED))).scalar()

    by_severity = {}
    for severity in AlertSeverity:
        count = (await db.execute(select(func.count()).select_from(Alert).filter(Alert.severity == severity))).scalar()
        by_severity[severity.value] = count'''

content = content.replace(old_stats, new_stats)

with open('d:/Users/feng/Desktop/ai/Antigravity/ops-platform/backend/app/api/v1/alerts.py', 'w', encoding='utf-8') as f:
    f.write(content)
