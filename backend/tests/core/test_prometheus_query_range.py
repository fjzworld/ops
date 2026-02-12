import pytest
import respx
from httpx import Response
from app.core.prometheus import PrometheusClient
from app.core.config import settings

@pytest.mark.asyncio
async def test_query_range_success():
    client = PrometheusClient()
    prometheus_url = f"{settings.PROMETHEUS_URL}/api/v1/query_range"
    
    mock_response = {
        "status": "success",
        "data": {
            "resultType": "matrix",
            "result": [
                {
                    "metric": {
                        "instance": "node1",
                        "resource_id": "1"
                    },
                    "values": [
                        [1644567890, "10.5"],
                        [1644567950, "11.2"]
                    ]
                }
            ]
        }
    }
    
    with respx.mock:
        respx.get(prometheus_url).mock(return_value=Response(200, json=mock_response))
        
        results = await client.query_range(
            query='up',
            start=1644567890,
            end=1644567950,
            step='60s'
        )
        
        assert len(results) == 1
        assert results[0]["metric"]["resource_id"] == "1"
        assert len(results[0]["values"]) == 2
        assert results[0]["values"][0][1] == "10.5"

@pytest.mark.asyncio
async def test_query_range_error():
    client = PrometheusClient()
    prometheus_url = f"{settings.PROMETHEUS_URL}/api/v1/query_range"
    
    with respx.mock:
        respx.get(prometheus_url).mock(return_value=Response(500))
        
        results = await client.query_range(
            query='up',
            start=1644567890,
            end=1644567950,
            step='60s'
        )
        assert results == []
