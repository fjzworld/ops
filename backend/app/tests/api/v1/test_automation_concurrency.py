import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.core.database import get_db, Base
from app.models.task import Task, TaskStatus
from app.tasks.automation import run_automation_task, summarize_automation_results, execute_single_resource

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

@patch("app.tasks.automation.chord")
@patch("app.tasks.automation.group")
@patch("app.tasks.automation.execute_single_resource")
@patch("app.tasks.automation.summarize_automation_results")
def test_run_automation_task_dispatcher(mock_summarize, mock_execute, mock_group, mock_chord, db):
    """
    Test Dispatcher:
    - Setup a Task with 2 target resources.
    - Call run_automation_task(task_id).
    - Verify chord was called with a group containing 2 execute_single_resource.s() signatures.
    """
    # 1. Setup Data
    task = Task(
        id=200,
        name="parallel-task",
        task_type="script",
        script_content="echo parallel",
        target_resources=[101, 102],
        status=TaskStatus.PENDING,
        execution_count=0,
        success_count=0,
        failure_count=0
    )
    db.add(task)
    db.commit()

    # Mock the signatures and group
    mock_execute.s.side_effect = lambda t_id, r_id: f"sig_execute_{t_id}_{r_id}"
    mock_summarize.s.side_effect = lambda t_id: f"sig_summarize_{t_id}"
    mock_group.return_value = "mock_group_obj"
    
    # Mock chord to return a callable
    mock_chord_instance = MagicMock()
    mock_chord.return_value = mock_chord_instance

    # 2. Call run_automation_task
    with patch("app.tasks.automation.SessionLocal", return_value=db):
        # With bind=True, calling the task object directly injects 'self'
        run_automation_task(200)

    # 3. Assertions
    # Fetch task again from DB to see changes
    task = db.query(Task).filter(Task.id == 200).first()
    assert task.status == TaskStatus.RUNNING
    assert task.execution_count == 1

    # Verify group was called with expected signatures
    expected_signatures = ["sig_execute_200_101", "sig_execute_200_102"]
    # Since we used a generator expression in group(), we need to check how it was called
    # group(execute_single_resource.s(task_id, res_id) for res_id in target_resource_ids)
    args, _ = mock_group.call_args
    # Convert generator to list if necessary
    actual_sigs = list(args[0])
    assert actual_sigs == expected_signatures

    # Verify chord was called with the group and callback
    expected_callback = "sig_summarize_200"
    mock_chord.assert_called_once_with("mock_group_obj")
    mock_chord_instance.assert_called_once_with(expected_callback)

def test_summarize_automation_results_aggregator(db):
    """
    Test Aggregator:
    - Call summarize_automation_results directly with a list of mock results (one success, one fail).
    - Verify the Task in DB is updated correctly.
    """
    # 1. Setup Data
    task = Task(
        id=300,
        name="aggregator-task",
        task_type="script", # Added missing field
        status=TaskStatus.RUNNING,
        success_count=0,
        failure_count=0,
        last_output=""
    )
    db.add(task)
    db.commit()

    mock_results = [
        {"resource_id": 101, "status": "success", "output": "Output Success", "exit_code": 0},
        {"resource_id": 102, "status": "failed", "output": "Output Failed", "exit_code": 1}
    ]

    # 2. Call summarize_automation_results
    with patch("app.tasks.automation.SessionLocal", return_value=db):
        summarize_automation_results(mock_results, 300)

    # 3. Assertions
    # Fetch task again from DB to see changes
    task = db.query(Task).filter(Task.id == 300).first()
    assert task.status == TaskStatus.FAILED
    assert task.success_count == 1
    assert task.failure_count == 1
    assert "Output Success" in task.last_output
    assert "Output Failed" in task.last_output
    assert "Execution failed on 1 resources" in task.last_error
