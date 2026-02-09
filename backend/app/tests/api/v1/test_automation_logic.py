import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.core.database import get_db, Base
from app.models.task import Task, TaskStatus
from app.models.resource import Resource, ResourceType, ResourceStatus
from app.tasks.automation import run_automation_task

# Setup Testing DB
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture
def db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@patch("paramiko.SSHClient")
@patch("app.tasks.automation.decrypt_string")
def test_run_automation_task_logic(mock_decrypt, mock_ssh_client, db):
    # 1. Setup Mock
    mock_decrypt.return_value = "decrypted_password"
    mock_ssh = MagicMock()
    mock_ssh_client.return_value = mock_ssh
    
    mock_stdout = MagicMock()
    mock_stdout.read.return_value = b"Hello from remote"
    mock_stdout.channel.recv_exit_status.return_value = 0
    
    mock_stderr = MagicMock()
    mock_stderr.read.return_value = b""
    
    mock_ssh.exec_command.return_value = (MagicMock(), mock_stdout, mock_stderr)

    # 2. Setup Data
    resource = Resource(
        id=1,
        name="test-server",
        type=ResourceType.PHYSICAL,
        status=ResourceStatus.ACTIVE,
        ip_address="1.2.3.4",
        ssh_username="root",
        ssh_password_enc="encrypted_pass"
    )
    db.add(resource)
    
    task = Task(
        id=100,
        name="test-task",
        task_type="script",
        script_content="echo hello",
        target_resources=[1],
        status=TaskStatus.PENDING
    )
    db.add(task)
    db.commit()

    # 3. Run Task Logic (manually call the function, bypassing Celery wrapper for pure logic test)
    # We need to mock SessionLocal in automation.py to use our test DB
    with patch("app.tasks.automation.SessionLocal", return_value=db):
        run_automation_task(100)

    # 4. Assertions
    db.refresh(task)
    assert task.status == TaskStatus.SUCCESS
    assert "Hello from remote" in task.last_output
    assert task.execution_count == 1
    assert task.success_count == 1
    
    mock_ssh.connect.assert_called_with(
        hostname="1.2.3.4",
        port=22,
        username="root",
        password="decrypted_password",
        timeout=15
    )
    mock_ssh.exec_command.assert_called_with("echo hello", timeout=300)
