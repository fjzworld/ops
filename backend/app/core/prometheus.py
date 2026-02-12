import httpx
import logging
from typing import List, Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

class PrometheusClient:
    """Client for interacting with Prometheus API"""
    
    def __init__(self, base_url: str = ""):
        self.base_url = (base_url or settings.PROMETHEUS_URL).rstrip("/")
        self.query_url = f"{self.base_url}/api/v1/query"
        self.query_range_url = f"{self.base_url}/api/v1/query_range"

    async def query_range(self, query: str, start: float, end: float, step: str = "60s") -> List[dict]:
        params = {
            "query": query,
            "start": start,
            "end": end,
            "step": step
        }
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    self.query_range_url,
                    params=params
                )
                
                if response.status_code != 200:
                    logger.error(f"Prometheus query_range failed with status {response.status_code}: {response.text}")
                    return []
                
                data = response.json()
                if data.get("status") != "success":
                    logger.error(f"Prometheus API returned error: {data.get('error', 'Unknown error')}")
                    return []
                
                return data.get("data", {}).get("result", [])
                
        except httpx.RequestError as e:
            logger.error(f"Connection error to Prometheus at {self.base_url}: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error querying Prometheus range: {e}")
            return []

    async def query_active_resources(self, window: str = "2m") -> List[int]:
        """
        Query Prometheus for active resources within the specified window.
        Uses the 'integrated-agent' job and 'up' metric.
        """
        query = f'count_over_time(up{{job="integrated-agent"}}[{window}])'
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    self.query_url,
                    params={"query": query}
                )
                
                if response.status_code != 200:
                    logger.error(f"Prometheus query failed with status {response.status_code}: {response.text}")
                    return []
                
                data = response.json()
                if data.get("status") != "success":
                    logger.error(f"Prometheus API returned error: {data.get('error', 'Unknown error')}")
                    return []
                
                results = data.get("data", {}).get("result", [])
                resource_ids = []
                
                for item in results:
                    # Metric value is a list [timestamp, "value"]
                    # We check if value > 0
                    try:
                        value = float(item.get("value", [0, "0"])[1])
                        if value > 0:
                            resource_id_str = item.get("metric", {}).get("resource_id")
                            if resource_id_str:
                                resource_ids.append(int(resource_id_str))
                    except (ValueError, IndexError, TypeError) as e:
                        logger.warning(f"Failed to parse prometheus result: {item}. Error: {e}")
                        continue
                
                return resource_ids
                
        except httpx.RequestError as e:
            logger.error(f"Connection error to Prometheus at {self.base_url}: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error querying Prometheus: {e}")
            return []
