import re

with open('d:/Users/feng/Desktop/ai/Antigravity/ops-platform/backend/app/api/v1/resources.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Update imports
content = content.replace('from app.models.task import Task, TaskStatus', 'from app.models.operation import Operation, OperationType, OperationStatus\nfrom app.models.task import TaskStatus')

old_task_creation = '''        task = Task(
            name=f"Deploy Alloy to {resource.ip_address}",
            description=f"Automated Alloy agent deployment for resource {resource.id}",
            task_type="deploy_alloy",
            target_resources=[resource_id],
            status=TaskStatus.PENDING,
            created_by=current_user.username,
        )
        db.add(task)
        await db.commit()
        await db.refresh(task)

        deploy_alloy_task.delay(
            task.id,'''

new_operation_creation = '''        operation = Operation(
            name=f"Deploy Alloy to {resource.ip_address}",
            description=f"Automated Alloy agent deployment for resource {resource.id}",
            operation_type=OperationType.SCRIPT_EXEC,
            config={"deployment_type": "alloy"},
            target_resources=[resource_id],
            status=OperationStatus.PENDING,
            created_by=current_user.username,
        )
        db.add(operation)
        await db.commit()
        await db.refresh(operation)

        deploy_alloy_task.delay(
            operation.id,'''

content = content.replace(old_task_creation, new_operation_creation)

with open('d:/Users/feng/Desktop/ai/Antigravity/ops-platform/backend/app/api/v1/resources.py', 'w', encoding='utf-8') as f:
    f.write(content)
