import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.main import app
from app.models.resource import Resource, ResourceType, ResourceStatus

@pytest.mark.asyncio
async def test_list_resources_async(db: AsyncSession, client: AsyncClient):
    # Setup
    res = Resource(name="async-test", type=ResourceType.PHYSICAL, status=ResourceStatus.ACTIVE)
    db.add(res)
    await db.commit()

    # Act
    response = await client.get("/api/v1/resources/")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert any(r["name"] == "async-test" for r in data)

@pytest.mark.asyncio
async def test_get_resource_async(db: AsyncSession, client: AsyncClient):
    # Setup
    res = Resource(name="async-detail", type=ResourceType.VIRTUAL, status=ResourceStatus.ACTIVE)
    db.add(res)
    await db.commit()
    await db.refresh(res)

    # Act
    response = await client.get(f"/api/v1/resources/{res.id}")

    # Assert
    assert response.status_code == 200
    assert response.json()["name"] == "async-detail"
