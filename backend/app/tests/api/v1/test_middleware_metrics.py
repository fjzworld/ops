import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.core.database import get_db, Base
from app.models.middleware import Middleware
from app.models.resource import Resource, ResourceType, ResourceStatus

# Use an in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

@pytest.fixture
def db():
    # Create the database tables
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        # Drop the database tables after the test
        Base.metadata.drop_all(bind=engine)

def test_get_middleware_metrics_endpoint_exists(db):
    # Setup: Create a resource and a middleware
    resource = Resource(
        name="test-resource",
        type=ResourceType.PHYSICAL,
        status=ResourceStatus.ACTIVE,
        ip_address="127.0.0.1"
    )
    db.add(resource)
    db.commit()
    db.refresh(resource)

    middleware = Middleware(
        name="test-middleware",
        type="mysql",
        resource_id=resource.id,
        port=3306,
        service_name="mysql",
        log_path="/var/log/mysql/error.log",
        status="active"
    )
    db.add(middleware)
    db.commit()
    db.refresh(middleware)

    # Act: Call the metrics endpoint
    # Note: We expect 401 because of auth, but 404 would mean endpoint doesn't exist
    response = client.get(f"/api/v1/middlewares/{middleware.id}/metrics")

    # Assert: Should not be 404 (Not Found)
    # Ideally we'd auth, but for "existence check", !404 is enough proof it's registered
    # However, since we need to fix it, let's aim for the actual behavior.
    # Without auth header, it should be 401. If it returns 404, the path is missing.
    assert response.status_code != 404, "Endpoint /api/v1/middlewares/{id}/metrics not found"
