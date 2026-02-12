from unittest.mock import MagicMock, patch, AsyncMock
import pytest
import sys
import os

# Add the backend directory to sys.path
sys.path.append(os.path.join(os.getcwd(), "ops-platform", "backend"))

# We will try to import sync_resource_status, it should fail initially
try:
    from app.tasks.monitoring import sync_resource_status
except ImportError:
    sync_resource_status = None

from app.models.resource import ResourceStatus

@patch("app.tasks.monitoring.PrometheusClient")
@patch("app.tasks.monitoring.SessionLocal")
@patch("app.tasks.monitoring.func")
def test_sync_resource_status_success(mock_func, mock_session_local, mock_prometheus_client):
    if sync_resource_status is None:
        pytest.fail("sync_resource_status not imported")

    # Setup mocks
    mock_prometheus = mock_prometheus_client.return_value
    mock_prometheus.query_active_resources = AsyncMock(return_value=[1, 2])
    
    mock_db = MagicMock()
    mock_session_local.return_value = mock_db
    
    # Mock return value for update()
    mock_query = MagicMock()
    mock_db.query.return_value = mock_query
    mock_query.filter.return_value = mock_query
    mock_query.update.side_effect = [5, 2] # 5 active, 2 offline
    
    # Execute task
    result = sync_resource_status()
    
    # Assertions
    mock_prometheus.query_active_resources.assert_called_once_with(window="2m")
    
    # Check if DB was queried and updated
    assert mock_db.query.call_count == 2
    assert mock_query.update.call_count == 2
    
    mock_db.commit.assert_called_once()
    mock_db.close.assert_called_once()
    
    assert "Synced status: 5 active, 2 offline" in result

def test_sync_resource_status_import_fails():
    assert sync_resource_status is not None, "sync_resource_status should be defined"
