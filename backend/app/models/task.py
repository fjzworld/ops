from sqlalchemy import Column, Integer, String, Text, Boolean, JSON, DateTime, Enum as SQLEnum, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum
from typing import List



class TaskStatus(str, enum.Enum):
    """Task execution status"""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"



class Task(Base):
    """Automation task model"""
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(String(500))
    
    # Task configuration
    task_type = Column(String(50), nullable=False)  # script, ansible, terraform
    script_content = Column(Text)
    script_path = Column(String(255))
    parameters = Column(JSON, default=dict)
    
    # Execution settings
    target_resources = Column(JSON, default=list)  # List of resource IDs
    schedule = Column(String(100))  # Cron expression
    enabled = Column(Boolean, default=True)
    
    # Execution tracking
    status = Column(SQLEnum(TaskStatus), default=TaskStatus.PENDING)
    last_run_at = Column(DateTime(timezone=True))
    next_run_at = Column(DateTime(timezone=True))
    execution_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    failure_count = Column(Integer, default=0)
    
    # Results
    last_output = Column(Text)
    last_error = Column(Text)
    
    executions = relationship("TaskExecution", back_populates="task", cascade="all, delete-orphan")
    
    # Timestamps

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(String(100))
    
    def __repr__(self):
        return f"<Task(name='{self.name}', status='{self.status}')>"


class TaskExecution(Base):
    """Task execution history model"""
    __tablename__ = "task_executions"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False, index=True)
    status = Column(SQLEnum(TaskStatus), nullable=False)
    start_time = Column(DateTime(timezone=True), server_default=func.now())
    end_time = Column(DateTime(timezone=True))
    output = Column(Text)
    error = Column(Text)
    
    task = relationship("Task", back_populates="executions")

    def __repr__(self):
        return f"<TaskExecution(task_id={self.task_id}, status='{self.status}')>"

