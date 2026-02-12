from unittest.mock import MagicMock, patch, AsyncMock
import pytest
from fastapi.testclient import TestClient
import sys
import os

# Add the backend directory to sys.path
sys.path.append(os.path.join(os.getcwd(), "ops-platform", "backend"))

from app.main import app
from app.models.resource import Resource
from app.api.v1.auth import get_current_active_user
from app.core.database import get_async_db

@pytest.fixture
def client():
    return TestClient(app)

@patch("app.api.v1.resources.deploy_alloy_task")
def test_deploy_alloy_monitoring_agent_async(mock_task, client):
    # Setup mocks
    mock_user = MagicMock(username="admin")
    app.dependency_overrides[get_current_active_user] = lambda: mock_user
    
    mock_db = AsyncMock()
    app.dependency_overrides[get_async_db] = lambda: mock_db
    
    mock_resource = Resource(id=1, ip_address="1.2.3.4", name="test-node")
    mock_db.get.return_value = mock_resource
    
    # Mock Task creation
    async def mock_refresh(obj):
        obj.id = 123
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock(side_effect=mock_refresh)
    
    # Payload
    payload = {
        "ip_address": "1.2.3.4",
        "ssh_port": 22,
        "ssh_username": "root",
        "ssh_password": "password",
        "backend_url": "http://backend:8000"
    }
    
    # Execute
    response = client.post("/api/v1/resources/1/deploy-alloy", json=payload)
    
    # Assertions
    assert response.status_code == 200
    data = response.json()
    assert data["task_id"] == 123
    assert "Deployment started" in data["message"]
    
    # Verify Task was created
    assert mock_db.add.called
    # Verify celery task was triggered
    mock_task.delay.assert_called_once_with(
        123, 
        1, 
        "http://backend:8000",
        ssh_username="root",
        ssh_password="password",
        ssh_private_key=None,
        ssh_port=22
    )
    
    # Cleanup
    app.dependency_overrides = {}
