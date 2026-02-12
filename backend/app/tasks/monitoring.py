import asyncio
import logging
from sqlalchemy import func
from app.tasks.celery_app import celery_app
from app.core.prometheus import PrometheusClient
from app.core.database import SessionLocal
from app.models.resource import Resource, ResourceStatus

logger = logging.getLogger(__name__)

@celery_app.task(name="sync_resource_status")
def sync_resource_status():
    """
    Sync resource status from Prometheus to Database.
    Resources seen in Prometheus in the last 2m are marked ACTIVE.
    Others are marked OFFLINE.
    """
    try:
        # Create a new event loop for this thread if necessary, or use asyncio.run
        # Celery workers run in threads or processes.
        # 1. Get active resources
        client = PrometheusClient()
        active_ids = asyncio.run(client.query_active_resources(window="2m"))
        
        # 2. Get current metrics for active resources
        # We need to query Prometheus for CPU/Mem/Disk for all these resources
        # Since query_active_resources returns IDs, we can use that to update status.
        # But to get values, we need separate queries.
        
        # Query 1: CPU Usage (Avg over last 2m)
        # 100 - (avg by (resource_id) (irate(node_cpu_seconds_total{mode="idle"}[2m])) * 100)
        cpu_query = '100 - (avg by (resource_id) (irate(node_cpu_seconds_total{mode="idle"}[2m])) * 100)'
        
        # Query 2: Memory Usage
        # (node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes * 100
        mem_query = '(node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes * 100'
        
        # Query 3: Disk Usage (Root partition)
        # 100 - ((node_filesystem_avail_bytes{mountpoint="/"} * 100) / node_filesystem_size_bytes{mountpoint="/"})
        disk_query = '100 - ((node_filesystem_avail_bytes{mountpoint="/"} * 100) / node_filesystem_size_bytes{mountpoint="/"})'

        async def fetch_metrics():
             async with httpx.AsyncClient(timeout=10.0) as http_client:
                # Reuse client query method logic or just use http_client directly for batch
                # Ideally PrometheusClient should have a query method, checking that
                # It has query_active_resources and query_range but not simple query
                # Let's add simple query to PrometheusClient or just use what we have.
                # Actually query_active_resources used query_url directly.
                # Let's instantiate client and use its internal URL
                
                resp_cpu = await http_client.get(client.query_url, params={"query": cpu_query})
                resp_mem = await http_client.get(client.query_url, params={"query": mem_query})
                resp_disk = await http_client.get(client.query_url, params={"query": disk_query})
                return resp_cpu.json(), resp_mem.json(), resp_disk.json()

        import httpx
        cpu_data, mem_data, disk_data = asyncio.run(fetch_metrics())
        
        # Parse metrics into a dict {resource_id: {cpu, mem, disk}}
        metrics_map = {}
        
        def parse_prom_result(data, metric_name):
            results = data.get("data", {}).get("result", [])
            for item in results:
                try:
                    res_id_str = item.get("metric", {}).get("resource_id")
                    if not res_id_str: continue
                    res_id = int(res_id_str)
                    val = float(item.get("value", [0, "0"])[1])
                    if res_id not in metrics_map: metrics_map[res_id] = {}
                    metrics_map[res_id][metric_name] = val
                except: continue

        parse_prom_result(cpu_data, "cpu_usage")
        parse_prom_result(mem_data, "memory_usage")
        parse_prom_result(disk_data, "disk_usage")

    except Exception as e:
        logger.error(f"Failed to query metrics from Prometheus: {e}")
        return f"Error: {e}"

    db = SessionLocal()
    try:
        active_count = 0
        
        # Batch update active status and metrics
        if active_ids:
             # First mark all active as active
             db.query(Resource).filter(Resource.id.in_(active_ids)).update(
                {Resource.status: ResourceStatus.ACTIVE, Resource.last_seen: func.now()},
                synchronize_session=False
            )
             active_count = len(active_ids)
        
        # Now update metrics for each resource that has them
        # Validating bulk update might be complex with SQLAlchemy 1.4/2.0+ and different DBs
        # Simple loop might be okay if number of resources is small (<100)
        # For larger scale, bulk_update_mappings is better.
        
        updates = []
        for rid, metrics in metrics_map.items():
            updates.append({
                "id": rid,
                "cpu_usage": metrics.get("cpu_usage"),
                "memory_usage": metrics.get("memory_usage"),
                "disk_usage": metrics.get("disk_usage")
            })
            
        if updates:
            db.bulk_update_mappings(Resource, updates)

        # Mark Offline
        offline_query = db.query(Resource).filter(Resource.status != ResourceStatus.OFFLINE)
        if active_ids:
            offline_query = offline_query.filter(~Resource.id.in_(active_ids))
            
        offline_count = offline_query.update(
            {Resource.status: ResourceStatus.OFFLINE},
            synchronize_session=False
        )

        db.commit()
        msg = f"Synced status: {active_count} active (with metrics), {offline_count} offline"
        logger.info(msg)
        return msg
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to sync resource status to database: {e}")
        return f"Error: {e}"
    finally:
        db.close()
