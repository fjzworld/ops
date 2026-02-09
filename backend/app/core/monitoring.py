import logging
from prometheus_client import Gauge

logger = logging.getLogger(__name__)

# Define Prometheus Metrics
# Labels: resource_id, resource_name, ip_address

CPU_USAGE = Gauge(
    'opspro_cpu_usage_percent',
    'CPU Usage Percentage',
    ['resource_id', 'resource_name', 'ip_address']
)

MEMORY_USAGE = Gauge(
    'opspro_memory_usage_percent',
    'Memory Usage Percentage',
    ['resource_id', 'resource_name', 'ip_address']
)

DISK_USAGE = Gauge(
    'opspro_disk_usage_percent',
    'Disk Usage Percentage',
    ['resource_id', 'resource_name', 'ip_address']
)

NETWORK_IN = Gauge(
    'opspro_network_in_mb',
    'Network Incoming Traffic (MB/s)',
    ['resource_id', 'resource_name', 'ip_address']
)

NETWORK_OUT = Gauge(
    'opspro_network_out_mb',
    'Network Outgoing Traffic (MB/s)',
    ['resource_id', 'resource_name', 'ip_address']
)


DISK_PARTITION_USAGE = Gauge(
    'opspro_disk_partition_percent',
    'Disk Partition Usage Percentage',
    ['resource_id', 'resource_name', 'ip_address', 'mountpoint', 'device']
)

DISK_PARTITION_TOTAL = Gauge(
    'opspro_disk_partition_total_gb',
    'Disk Partition Total Size (GB)',
    ['resource_id', 'resource_name', 'ip_address', 'mountpoint', 'device']
)

DISK_PARTITION_USED = Gauge(
    'opspro_disk_partition_used_gb',
    'Disk Partition Used Size (GB)',
    ['resource_id', 'resource_name', 'ip_address', 'mountpoint', 'device']
)


def update_metrics(resource_id: str, resource_name: str, ip_address: str, metrics: dict):
    """
    Update Prometheus metrics for a resource
    """
    labels = {
        'resource_id': str(resource_id),
        'resource_name': resource_name,
        'ip_address': ip_address
    }

    if 'cpu_usage' in metrics:
        CPU_USAGE.labels(**labels).set(metrics['cpu_usage'])

    if 'memory_usage' in metrics:
        MEMORY_USAGE.labels(**labels).set(metrics['memory_usage'])

    if 'disk_usage' in metrics:
        DISK_USAGE.labels(**labels).set(metrics['disk_usage'])

    if 'network_in' in metrics:
        NETWORK_IN.labels(**labels).set(metrics.get('network_in', 0))

    if 'network_out' in metrics:
        NETWORK_OUT.labels(**labels).set(metrics.get('network_out', 0))

    if 'disk_partitions' in metrics and metrics['disk_partitions']:
        for part in metrics['disk_partitions']:
            # Handle both dict and Pydantic model
            is_dict = isinstance(part, dict)
            mountpoint = part.get('mountpoint', 'unknown') if is_dict else part.mountpoint
            device = part.get('device', 'unknown') if is_dict else part.device
            
            # 后端双重过滤: 忽略系统和容器挂载点
            if mountpoint.startswith(('/boot', '/snap', '/run', '/sys', '/dev', '/proc', '/var/lib/docker', '/var/lib/kubelet', '/var/lib/containerd')):
                continue

            part_labels = {
                **labels,
                'mountpoint': mountpoint,
                'device': device
            }
            try:
                percent = part.get('percent', 0) if is_dict else part.percent
                total = part.get('total_gb', 0) if is_dict else part.total_gb
                used = part.get('used_gb', 0) if is_dict else part.used_gb
                
                DISK_PARTITION_USAGE.labels(**part_labels).set(percent)
                DISK_PARTITION_TOTAL.labels(**part_labels).set(total)
                DISK_PARTITION_USED.labels(**part_labels).set(used)
            except Exception as e:
                logger.error(f"Failed to update partition metric: {e}")


def clear_metrics(resource_id: str, resource_name: str, ip_address: str):
    """
    Clear Prometheus metrics for a resource when it goes offline or is deleted.
    This prevents stale metrics from accumulating.
    """
    labels = {
        'resource_id': str(resource_id),
        'resource_name': resource_name,
        'ip_address': ip_address
    }

    try:
        # Remove metrics for this resource
        CPU_USAGE.remove(*labels.values())
        MEMORY_USAGE.remove(*labels.values())
        DISK_USAGE.remove(*labels.values())
        NETWORK_IN.remove(*labels.values())
        NETWORK_OUT.remove(*labels.values())
        logger.info(f"Cleared Prometheus metrics for resource {resource_id} ({resource_name})")
    except Exception as e:
        # Metrics might not exist, that's okay
        logger.debug(f"Could not clear metrics for resource {resource_id}: {e}")


def update_resource_status(resource_id: str, resource_name: str, ip_address: str, is_online: bool):
    """
    Update resource online status. If offline, clear its metrics.
    """
    if not is_online:
        clear_metrics(resource_id, resource_name, ip_address)
        logger.info(f"Resource {resource_id} ({resource_name}) marked as offline, metrics cleared")
    else:
        logger.debug(f"Resource {resource_id} ({resource_name}) is online")
