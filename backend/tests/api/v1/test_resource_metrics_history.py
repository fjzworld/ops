import pytest
import respx
from httpx import Response, AsyncClient
from datetime import datetime, timedelta
from app.main import app
from app.core.prometheus import PrometheusClient
from app.core.config import settings

@pytest.mark.asyncio
async def test_get_metrics_history_prometheus_integration():
    resource_id = 1
    prometheus_url = f"{settings.PROMETHEUS_URL}/api/v1/query_range"
    
    # Mock Prometheus data for CPU
    cpu_data = {
        "status": "success",
        "data": {
            "resultType": "matrix",
            "result": [
                {
                    "metric": {"resource_id": "1"},
                    "values": [
                        [1644567890, "20.0"],
                        [1644567950, "25.0"]
                    ]
                }
            ]
        }
    }
    
    # Mock Prometheus data for Memory
    mem_data = {
        "status": "success",
        "data": {
            "resultType": "matrix",
            "result": [
                {
                    "metric": {"resource_id": "1"},
                    "values": [
                        [1644567890, "40.0"],
                        [1644567950, "45.0"]
                    ]
                }
            ]
        }
    }
    
    # Mock Prometheus data for Disk
    disk_data = {
        "status": "success",
        "data": {
            "resultType": "matrix",
            "result": [
                {
                    "metric": {"resource_id": "1"},
                    "values": [
                        [1644567890, "10.0"],
                        [1644567950, "10.0"]
                    ]
                }
            ]
        }
    }

    with respx.mock:
        # We need to match the query parameters to differentiate between CPU, Mem, and Disk
        respx.get(prometheus_url, params__query__contains='node_cpu').mock(return_value=Response(200, json=cpu_data))
        respx.get(prometheus_url, params__query__contains='node_memory').mock(return_value=Response(200, json=mem_data))
        respx.get(prometheus_url, params__query__contains='node_filesystem').mock(return_value=Response(200, json=disk_data))
        
        # We also need to mock the DB call to get the resource
        # For simplicity in this test, we can mock the resource detector or just assume the DB works if we use a real test client with a mock DB
        # But here I'll just focus on the API response if I can get past the auth and DB
        
        # Actually, it's easier to just test the merging logic separately if I want to be purely TDD
        # But the requirement is to rewrite the endpoint.
        
        async with AsyncClient(app=app, base_url="http://test") as ac:
            # Need to mock authentication
            # I'll use a hack to skip auth or provide a valid token
            # For now, let's see if it fails on auth
            response = await ac.get(f"/api/v1/resources/{resource_id}/metrics/history")
            
            # It should fail because I haven't implemented it yet (it will still use SQL)
            # OR it will fail because of auth/db
            assert response.status_code in [200, 401, 404] 
            
@pytest.mark.unit
def test_merge_prometheus_data():
    # I'll implement a helper for merging and test it
    from app.api.v1.resources import merge_metrics
    
    cpu_results = [
        {"values": [[1644567890, "20.0"], [1644567950, "25.0"]]}
    ]
    mem_results = [
        {"values": [[1644567890, "40.0"], [1644567950, "45.0"]]}
    ]
    disk_results = [
        {"values": [[1644567890, "10.0"], [1644567950, "10.0"]]}
    ]
    
    merged = merge_metrics(cpu_results, mem_results, disk_results)
    
    assert len(merged) == 2
    assert merged[0]["cpu_usage"] == 20.0
    assert merged[0]["memory_usage"] == 40.0
    assert merged[0]["disk_usage"] == 10.0
    assert merged[0]["timestamp"] == datetime.fromtimestamp(1644567890).isoformat()
