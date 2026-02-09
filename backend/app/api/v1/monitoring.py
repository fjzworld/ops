import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User
from app.models.resource import Resource
from app.api.v1.auth import get_current_active_user
import httpx
import os

logger = logging.getLogger(__name__)
router = APIRouter()

PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://prometheus:9090")

# --- Prometheus Proxy Endpoints ---

@router.get("/query")
async def query_prometheus(
    query: str,
    time: float = None,
    current_user: User = Depends(get_current_active_user)
):
    """
    Proxy query to Prometheus (Instant Query)
    Example: query=opspro_cpu_usage_percent
    """
    params = {"query": query}
    if time:
        params["time"] = time
        
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{PROMETHEUS_URL}/api/v1/query", params=params)
            return resp.json()
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"Prometheus connection failed: {e}")

@router.get("/query_range")
async def query_range_prometheus(
    query: str,
    start: float,
    end: float,
    step: int = 60,
    current_user: User = Depends(get_current_active_user)
):
    """
    Proxy query to Prometheus (Range Query)
    Returns simplified format: [{time: timestamp, value: value}, ...]
    """
    params = {
        "query": query,
        "start": start,
        "end": end,
        "step": step
    }
        
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{PROMETHEUS_URL}/api/v1/query_range", params=params)
            prom_data = resp.json()
            
            # Transform Prometheus format to simplified format for frontend
            if prom_data.get("status") == "success":
                result = prom_data.get("data", {}).get("result", [])
                if result and len(result) > 0:
                    # Get values from first result (assuming single series query)
                    values = result[0].get("values", [])
                    # Transform [[timestamp, "value"], ...] to [{time: ts, value: val}, ...]
                    transformed = [{"time": v[0], "value": v[1]} for v in values]
                    return transformed
            
            return []
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"Prometheus connection failed: {e}")

# --- Existing Dashboard Endpoint (Legacy/Hybrid) ---

@router.get("/dashboard")
async def get_dashboard_data(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get dashboard monitoring data (V2: Management by Exception)
    """
    async with httpx.AsyncClient() as client:
        try:
            # 1. Fetch Real-time Data from Prometheus
            queries = {
                "all_cpu": "opspro_cpu_usage_percent",
                "all_mem": "opspro_memory_usage_percent"
            }
            
            prom_results = {}
            for key, q in queries.items():
                try:
                    resp = await client.get(f"{PROMETHEUS_URL}/api/v1/query", params={"query": q})
                    data = resp.json()
                    if data["status"] == "success" and data["data"]["result"]:
                        prom_results[key] = data["data"]["result"]
                    else:
                        prom_results[key] = []
                except Exception:
                    prom_results[key] = []

            # 2. Process Nodes Data
            nodes_data = [] # Combined CPU/Mem data keyed by IP or resource_id
            
            # Helper to parse prometheus result
            def parse_prom_result(results):
                parsed = {}
                for item in results:
                    metric = item["metric"]
                    # Prefer resource_id, fallback to instance/ip
                    rid = metric.get("resource_id") or metric.get("instance")
                    parsed[rid] = {
                        "id": metric.get("resource_id", "0"),
                        "name": metric.get("resource_name", "Unknown"),
                        "ip": metric.get("ip_address", metric.get("instance", "")),
                        "value": float(item["value"][1])
                    }
                return parsed

            cpu_map = parse_prom_result(prom_results.get("all_cpu", []))
            mem_map = parse_prom_result(prom_results.get("all_mem", []))
            
            # Merge CPU and Mem
            all_node_keys = set(cpu_map.keys()) | set(mem_map.keys())
            processed_nodes = []
            
            for key in all_node_keys:
                cpu_info = cpu_map.get(key, {})
                mem_info = mem_map.get(key, {})
                
                # Base info from whichever has it
                base_info = cpu_info if cpu_info else mem_info
                
                cpu_val = cpu_info.get("value", 0.0)
                mem_val = mem_info.get("value", 0.0)
                
                status = "normal"
                if cpu_val > 90 or mem_val > 90:
                    status = "critical"
                elif cpu_val > 80 or mem_val > 80:
                    status = "warning"
                    
                processed_nodes.append({
                    "id": base_info.get("id"),
                    "name": base_info.get("name"),
                    "ip": base_info.get("ip"),
                    "cpu": round(cpu_val, 1),
                    "memory": round(mem_val, 1),
                    "status": status
                })

            # 3. Calculate Distribution (CPU)
            # Buckets: 0-20, 20-40, 40-60, 60-80, 80-100
            distribution = {
                "0-20": 0, "20-40": 0, "40-60": 0, "60-80": 0, "80-100": 0
            }
            
            high_load_count = 0
            
            for node in processed_nodes:
                val = node["cpu"]
                if val > 80:
                    distribution["80-100"] += 1
                    high_load_count += 1
                elif val > 60:
                    distribution["60-80"] += 1
                elif val > 40:
                    distribution["40-60"] += 1
                elif val > 20:
                    distribution["20-40"] += 1
                else:
                    distribution["0-20"] += 1

            # 4. Get Summary Counts with stable offline detection
            from app.models.alert import Alert, AlertStatus, AlertSeverity
            from datetime import datetime, timedelta, timezone
            
            critical_alerts_count = db.query(Alert).filter(
                Alert.status == AlertStatus.FIRING,
                Alert.severity == AlertSeverity.CRITICAL
            ).count()
            
            # Get all resources from DB for stable offline detection
            all_db_resources = db.query(Resource).all()
            total_db_resources = len(all_db_resources)
            
            # Use last_seen + 90s threshold for stable online detection
            now = datetime.now(timezone.utc)
            offline_threshold = now - timedelta(seconds=90)
            
            online_resources = []
            offline_resources = []
            
            for res in all_db_resources:
                if res.last_seen and res.last_seen > offline_threshold:
                    online_resources.append(res)
                else:
                    offline_resources.append(res)
            
            online_count = len(online_resources)
            offline_count = len(offline_resources)
            
            # High load only counts from online nodes
            healthy_count = max(0, online_count - high_load_count)

            # 5. Top Critical Nodes
            # Sort by CPU desc
            processed_nodes.sort(key=lambda x: x["cpu"], reverse=True)
            top_critical_nodes = processed_nodes[:5]

            return {
                "summary": {
                    "critical_alerts": critical_alerts_count,
                    "high_load_nodes": high_load_count,
                    "offline_nodes": offline_count,
                    "healthy_nodes": healthy_count,
                    "total_resources": total_db_resources
                },
                "distribution": {
                    "cpu": distribution
                },
                "all_nodes": processed_nodes,  # All nodes for hex grid
                "top_nodes": top_critical_nodes  # Top 5 for list view
            }

        except Exception as e:
            logger.error(f"Dashboard data fetch failed: {e}", exc_info=True)
            # Fail gracefully
            return {
                "summary": {
                    "critical_alerts": 0, "high_load_nodes": 0, 
                    "offline_nodes": 0, "healthy_nodes": 0, "total_resources": 0
                },
                "distribution": {"cpu": {}},
                "top_nodes": []
            }
