import re

with open('d:/Users/feng/Desktop/ai/Antigravity/ops-platform/backend/app/tasks/deployment.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('from app.models.task import Task, TaskStatus', 'from app.models.operation import Operation, OperationStatus, OperationExecution')

# replace query
content = content.replace('task = db.query(Task).filter(Task.id == task_id).first()', 'task = db.query(Operation).filter(Operation.id == task_id).first()')

# replace TaskStatus
content = content.replace('TaskStatus', 'OperationStatus')

# replace TaskExecution
content = content.replace('from app.models.task import TaskExecution', '')
content = content.replace('execution = TaskExecution(', 'execution = OperationExecution(')
content = content.replace('task_id=task.id', 'operation_id=task.id, operation_type=task.operation_type')

with open('d:/Users/feng/Desktop/ai/Antigravity/ops-platform/backend/app/tasks/deployment.py', 'w', encoding='utf-8') as f:
    f.write(content)
