from sqlalchemy import Column, Integer, String, Text, Boolean, JSON, DateTime, Enum as SQLEnum, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class OperationType(str, enum.Enum):
    """Operation type enumeration"""
    SCRIPT_EXEC = "script_exec"
    FRONTEND_DEPLOY = "frontend_deploy"


class OperationStatus(str, enum.Enum):
    """Operation execution status"""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class Operation(Base):
    """Unified operations model — replaces Task"""
    __tablename__ = "operations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(String(500))

    # Operation type discriminator
    operation_type = Column(SQLEnum(OperationType), nullable=False, index=True)

    # Type-specific configuration (JSON)
    # script_exec: { "script_content": "...", "script_path": "...", "parameters": {}, "task_type": "shell" }
    # frontend_deploy: { "restart_keepalived": false, "filename": "dist.zip", "file_size": 12345 }
    config = Column(JSON, default=dict)

    # Execution settings
    target_resources = Column(JSON, default=list)  # List of resource IDs
    schedule = Column(String(100))  # Cron expression (only for script_exec)
    enabled = Column(Boolean, default=True)

    # Execution tracking
    status = Column(SQLEnum(OperationStatus), default=OperationStatus.PENDING)
    last_run_at = Column(DateTime(timezone=True))
    next_run_at = Column(DateTime(timezone=True))
    execution_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    failure_count = Column(Integer, default=0)

    # Results
    last_output = Column(Text)
    last_error = Column(Text)

    executions = relationship("OperationExecution", back_populates="operation", cascade="all, delete-orphan")

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(String(100))

    def __repr__(self):
        return f"<Operation(name='{self.name}', type='{self.operation_type}', status='{self.status}')>"


class OperationExecution(Base):
    """Operation execution history — replaces TaskExecution"""
    __tablename__ = "operation_executions"

    id = Column(Integer, primary_key=True, index=True)
    operation_id = Column(Integer, ForeignKey("operations.id"), nullable=False, index=True)
    operation_type = Column(SQLEnum(OperationType), nullable=False)  # Redundant for fast filtering
    status = Column(SQLEnum(OperationStatus), nullable=False)
    start_time = Column(DateTime(timezone=True), server_default=func.now())
    end_time = Column(DateTime(timezone=True))
    output = Column(Text)
    error = Column(Text)

    # Deploy-specific: step-by-step logs
    steps = Column(JSON, default=list)

    # Input snapshot for this execution
    input_data = Column(JSON, default=dict)

    operation = relationship("Operation", back_populates="executions")

    def __repr__(self):
        return f"<OperationExecution(operation_id={self.operation_id}, status='{self.status}')>"
