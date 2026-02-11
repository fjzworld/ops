import logging
import httpx
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.resource import Resource, ResourceStatus
from app.models.alert import Alert, AlertStatus, AlertSeverity

logger = logging.getLogger(__name__)

PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://prometheus:9090")

class MonitoringService:
    @staticmethod
    async def get_dashboard_stats(db: AsyncSession) -> Dict[str, Any]:
        """
        Fetch and aggregate dashboard stats from Prometheus and Database.
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
                        if data.get("status") == "success" and data.get("data", {}).get("result"):
                            prom_results[key] = data["data"]["result"]
                        else:
                            prom_results[key] = []
                    except Exception:
                        prom_results[key] = []

                # 2. Process Nodes Data
                def parse_prom_result(results):
                    parsed = {}
                    for item in results:
                        metric = item["metric"]
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
                
                all_node_keys = set(cpu_map.keys()) | set(mem_map.keys())
                processed_nodes = []
                
                for key in all_node_keys:
                    cpu_info = cpu_map.get(key, {})
                    mem_info = mem_map.get(key, {})
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

                # 3. Calculate Distribution
                distribution = {"0-20": 0, "20-40": 0, "40-60": 0, "60-80": 0, "80-100": 0}
                high_load_count = 0
                
                for node in processed_nodes:
                    val = node["cpu"]
                    if val > 80:
                        distribution["80-100"] += 1
                        high_load_count += 1
                    elif val > 60: distribution["60-80"] += 1
                    elif val > 40: distribution["40-60"] += 1
                    elif val > 20: distribution["20-40"] += 1
                    else: distribution["0-20"] += 1

                # 4. Database Summaries
                stmt_alerts = select(func.count(Alert.id)).filter(
                    Alert.status == AlertStatus.FIRING,
                    Alert.severity == AlertSeverity.CRITICAL
                )
                critical_alerts_count = (await db.execute(stmt_alerts)).scalar() or 0
                
                stmt_resources = select(Resource)
                result = await db.execute(stmt_resources)
                all_db_resources = result.scalars().all()
                
                now = datetime.now(timezone.utc)
                offline_threshold = now - timedelta(seconds=90)
                
                online_count = sum(1 for res in all_db_resources if res.last_seen and res.last_seen > offline_threshold)
                offline_count = len(all_db_resources) - online_count
                healthy_count = max(0, online_count - high_load_count)

                # Calculate averages for Monitoring Dashboard
                avg_cpu = sum(node["cpu"] for node in processed_nodes) / len(processed_nodes) if processed_nodes else 0
                avg_mem = sum(node["memory"] for node in processed_nodes) / len(processed_nodes) if processed_nodes else 0
                
                # Disk usage average from DB resources
                avg_disk = sum(res.disk_usage or 0 for res in all_db_resources) / len(all_db_resources) if all_db_resources else 0

                processed_nodes.sort(key=lambda x: x["cpu"], reverse=True)
                
                return {
                    "summary": {
                        "critical_alerts": critical_alerts_count,
                        "high_load_nodes": high_load_count,
                        "offline_nodes": offline_count,
                        "healthy_nodes": healthy_count,
                        "total_resources": len(all_db_resources)
                    },
                    "distribution": {"cpu": distribution},
                    "all_nodes": processed_nodes,
                    "top_nodes": processed_nodes[:5],
                    # Legacy/Monitoring Dashboard compatibility fields
                    "average_cpu_usage": round(avg_cpu, 1),
                    "average_memory_usage": round(avg_mem, 1),
                    "average_disk_usage": round(avg_disk, 1),
                    "top_cpu_resources": processed_nodes[:5]
                }

            except Exception as e:
                logger.error(f"Monitoring Service Error: {e}", exc_info=True)
                return {
                    "summary": {"critical_alerts": 0, "high_load_nodes": 0, "offline_nodes": 0, "healthy_nodes": 0, "total_resources": 0},
                    "distribution": {"cpu": {}},
                    "all_nodes": [],
                    "top_nodes": []
                }
