from unittest.mock import MagicMock, patch
import pytest
import sys
import os

# Add the backend directory to sys.path
sys.path.append(os.path.join(os.getcwd(), "ops-platform", "backend"))

from app.models.task import TaskStatus

def test_deploy_alloy_task_success():
    # Attempt to import the task (should fail until implemented)
    try:
        from app.tasks.deployment import deploy_alloy_task
    except ImportError:
        pytest.fail("deploy_alloy_task not implemented")

    with patch("app.tasks.deployment.SessionLocal") as mock_session_local, \
         patch("app.tasks.deployment.deploy_alloy_agent") as mock_deploy_agent, \
         patch("app.tasks.deployment.Resource") as mock_resource_model:
        
        # Setup DB mock
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        
        # Mock Task
        mock_task = MagicMock()
        mock_task.id = 1
        mock_db.query.return_value.filter.return_value.first.return_value = mock_task
        
        # Mock Resource and credentials
        mock_resource = MagicMock()
        mock_resource.id = 10
        mock_resource.ip_address = "1.2.3.4"
        mock_resource.ssh_port = 22
        mock_resource.ssh_username = "root"
        mock_resource.ssh_password = "password"
        mock_resource.ssh_private_key = None
        mock_db.query.return_value.get.return_value = mock_resource

        # Mock deploy_alloy_agent return value
        mock_deploy_agent.return_value = True

        # Execute
        deploy_alloy_task(
            task_id=1, 
            resource_id=10, 
            backend_url="http://backend:8000",
            ssh_username="root",
            ssh_password="password"
        )

        # Assertions
        assert mock_task.status == TaskStatus.SUCCESS
        assert "Deployment successful" in mock_task.last_output
        mock_db.commit.assert_called()
        mock_deploy_agent.assert_called_once()

def test_deploy_alloy_task_failure():
    try:
        from app.tasks.deployment import deploy_alloy_task
    except ImportError:
        pytest.fail("deploy_alloy_task not implemented")

    with patch("app.tasks.deployment.SessionLocal") as mock_session_local, \
         patch("app.tasks.deployment.deploy_alloy_agent") as mock_deploy_agent:
        
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        
        mock_task = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_task
        
        # Mock Resource and credentials
        mock_resource = MagicMock()
        mock_resource.id = 10
        mock_resource.ip_address = "1.2.3.4"
        mock_resource.ssh_port = 22
        mock_resource.ssh_username = "root"
        mock_resource.ssh_password = "password"
        mock_resource.ssh_private_key = None
        mock_db.query.return_value.get.return_value = mock_resource

        # Mock deploy_alloy_agent to raise exception
        mock_deploy_agent.side_effect = Exception("SSH connection failed")

        # Execute
        deploy_alloy_task(
            task_id=1, 
            resource_id=10, 
            backend_url="http://backend:8000",
            ssh_username="root",
            ssh_password="password"
        )

        # Assertions
        assert mock_task.status == TaskStatus.FAILED
        assert "SSH connection failed" in mock_task.last_error
        mock_db.commit.assert_called()
