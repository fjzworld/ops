import pytest
import respx
from httpx import Response
from app.core.prometheus import PrometheusClient
from app.core.config import settings

@pytest.mark.asyncio
async def test_query_active_resources_success():
    client = PrometheusClient()
    prometheus_url = f"{settings.PROMETHEUS_URL}/api/v1/query"
    
    mock_response = {
        "status": "success",
        "data": {
            "resultType": "vector",
            "result": [
                {
                    "metric": {
                        "job": "integrated-agent",
                        "resource_id": "101"
                    },
                    "value": [1644567890.123, "1"]
                },
                {
                    "metric": {
                        "job": "integrated-agent",
                        "resource_id": "102"
                    },
                    "value": [1644567890.123, "0"]
                },
                {
                    "metric": {
                        "job": "integrated-agent",
                        "resource_id": "103"
                    },
                    "value": [1644567890.123, "5"]
                }
            ]
        }
    }
    
    with respx.mock:
        respx.get(prometheus_url).mock(return_value=Response(200, json=mock_response))
        
        resource_ids = await client.query_active_resources(window="2m")
        
        # 101 has value "1" (>0)
        # 102 has value "0" (not >0)
        # 103 has value "5" (>0)
        assert sorted(resource_ids) == [101, 103]

@pytest.mark.asyncio
async def test_query_active_resources_error():
    client = PrometheusClient()
    prometheus_url = f"{settings.PROMETHEUS_URL}/api/v1/query"
    
    with respx.mock:
        respx.get(prometheus_url).mock(return_value=Response(500))
        
        resource_ids = await client.query_active_resources()
        assert resource_ids == []

@pytest.mark.asyncio
async def test_query_active_resources_connection_error():
    client = PrometheusClient()
    prometheus_url = f"{settings.PROMETHEUS_URL}/api/v1/query"
    
    with respx.mock:
        respx.get(prometheus_url).side_effect = Exception("Connection refused")
        
        resource_ids = await client.query_active_resources()
        assert resource_ids == []
