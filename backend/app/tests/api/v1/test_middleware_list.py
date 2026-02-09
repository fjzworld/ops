import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.main import app
from app.core.database import get_db, Base
from app.models.middleware import Middleware
from app.models.resource import Resource, ResourceType, ResourceStatus

# Use an in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False},
    poolclass=StaticPool # Important for in-memory DB shared access
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
    # Force use of this session in the app for the test duration
    # This is tricky because the app uses its own dependency injection.
    # We are already overriding get_db, but we need to make sure the override
    # uses THIS db session or at least one connected to the SAME in-memory engine.
    
    # Actually, override_get_db uses TestingSessionLocal which binds to 'engine'.
    # This fixture also uses TestingSessionLocal which binds to 'engine'.
    # Since engine is bound to "sqlite:///:memory:" with check_same_thread=False,
    # and connection sharing for in-memory DB in sqlalchemy requires keeping a connection open
    # or using StaticPool.
    
    # Let's fix the engine definition to use StaticPool for in-memory DB to be shared across threads/sessions
    try:
        yield db
    finally:
        db.close()
        # Drop the database tables after the test
        Base.metadata.drop_all(bind=engine)

def test_list_middlewares_includes_resource_info(db):
    # Setup: Create a resource and a middleware
    resource = Resource(
        name="test-resource-with-ip",
        type=ResourceType.PHYSICAL,
        status=ResourceStatus.ACTIVE,
        ip_address="192.168.1.100"
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

    # Act: Call the list middlewares endpoint
    # Use dependency override to bypass auth or just inspect what we can get
    # But wait, middlewares endpoint requires auth.
    # Let's override the auth dependency for this test.
    from app.api.v1.auth import get_current_active_user
    from app.models.user import User

    app.dependency_overrides[get_current_active_user] = lambda: User(username="test", role="admin")

    response = client.get("/api/v1/middlewares/")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    item = next(m for m in data if m["id"] == middleware.id)
    
    # Check if resource info is present
    assert "resource" in item, "Resource field missing in response"
    assert item["resource"] is not None
    assert item["resource"]["name"] == "test-resource-with-ip"
    assert item["resource"]["ip_address"] == "192.168.1.100"
