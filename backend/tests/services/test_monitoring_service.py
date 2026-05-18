import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))

from app.models.resource import Resource, ResourceStatus, ResourceType
from app.services.monitoring_service import MonitoringService


def make_resource(status: ResourceStatus, last_seen=None) -> Resource:
    return Resource(
        name=f"resource-{status.value.lower()}",
        type=ResourceType.PHYSICAL,
        status=status,
        last_seen=last_seen,
    )


def test_resource_summary_uses_status_not_last_seen():
    resources = [
        make_resource(ResourceStatus.ACTIVE),
        make_resource(ResourceStatus.OFFLINE),
        make_resource(ResourceStatus.INACTIVE),
        make_resource(ResourceStatus.MAINTENANCE),
    ]

    summary = MonitoringService.get_resource_summary(resources, high_load_count=0)

    assert summary["total_resources"] == 4
    assert summary["offline_nodes"] == 1
    assert summary["healthy_nodes"] == 1


def test_resource_summary_excludes_high_load_active_nodes_from_healthy_count():
    resources = [
        make_resource(ResourceStatus.ACTIVE),
        make_resource(ResourceStatus.ACTIVE),
        make_resource(ResourceStatus.OFFLINE),
    ]

    summary = MonitoringService.get_resource_summary(resources, high_load_count=1)

    assert summary["offline_nodes"] == 1
    assert summary["healthy_nodes"] == 1
