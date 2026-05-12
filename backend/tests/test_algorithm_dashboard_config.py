from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.v1.auth import get_current_active_user
from app.core.database import Base
from app.core.encryption import decrypt_string
from app.main import app
from app.models.user import User


SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    return TestClient(app)


def test_algorithm_dashboard_config_service_returns_none_when_missing(db):
    from app.services.algorithm_dashboard import AlgorithmDashboardConfigService

    config = AlgorithmDashboardConfigService.get_config(db)

    assert config is None


def test_algorithm_dashboard_config_service_encrypts_and_preserves_password(db):
    from app.schemas.algorithm_dashboard import AlgorithmDashboardConfigUpdate
    from app.services.algorithm_dashboard import AlgorithmDashboardConfigService

    created = AlgorithmDashboardConfigService.upsert_config(
        db,
        AlgorithmDashboardConfigUpdate(
            name="海南空管算法执行时间监控",
            host="192.168.1.228",
            port=3306,
            username="readonly",
            password_plain="secret-1",
            database_name="hn_kongguan",
            enabled=True,
        ),
    )

    assert created.password_enc
    assert decrypt_string(created.password_enc) == "secret-1"

    updated = AlgorithmDashboardConfigService.upsert_config(
        db,
        AlgorithmDashboardConfigUpdate(
            name="海南空管算法看板",
            host="192.168.1.229",
            port=3307,
            username="readonly_v2",
            database_name="hn_kongguan_v2",
            enabled=True,
        ),
    )

    assert updated.id == created.id
    assert updated.name == "海南空管算法看板"
    assert decrypt_string(updated.password_enc) == "secret-1"


def test_algorithm_runtime_dashboard_api_returns_dynamic_title(client):
    app.dependency_overrides[get_current_active_user] = lambda: User(
        username="tester",
        email="tester@example.com",
        hashed_password="x",
        role="admin",
    )

    with patch(
        "app.api.v1.dashboard.AlgorithmDashboardService.fetch_algorithm_runtime"
    ) as mock_fetch:
        mock_fetch.return_value = {
            "title": "海南空管算法看板",
            "month": "202509",
            "from_time": "2026-05-08T00:00:00+08:00",
            "to_time": "2026-05-08T03:00:00+08:00",
            "timezone": "Asia/Shanghai",
            "refresh_seconds": 5,
            "panels": [],
        }

        response = client.get(
            "/api/v1/dashboard/algorithm-runtime",
            params={
                "month": "202509",
                "from": "now-3h",
                "to": "now",
                "timezone": "Asia/Shanghai",
            },
        )

    app.dependency_overrides = {}

    assert response.status_code == 200
    assert response.json()["title"] == "海南空管算法看板"


def test_algorithm_runtime_config_api_returns_empty_when_unconfigured(client):
    app.dependency_overrides[get_current_active_user] = lambda: User(
        username="tester",
        email="tester@example.com",
        hashed_password="x",
        role="admin",
    )

    with patch(
        "app.api.v1.dashboard.AlgorithmDashboardConfigService.get_config_async"
    ) as mock_get:
        mock_get.return_value = {
            "configured": False,
            "name": None,
            "host": None,
            "port": None,
            "username": None,
            "database_name": None,
            "enabled": False,
            "has_password": False,
        }
        response = client.get("/api/v1/dashboard/algorithm-runtime/config")

    app.dependency_overrides = {}

    assert response.status_code == 200
    assert response.json()["configured"] is False


def test_algorithm_dashboard_config_connection_error_is_sanitized():
    from app.schemas.algorithm_dashboard import AlgorithmDashboardConfigTestRequest
    from app.services.algorithm_dashboard import AlgorithmDashboardConfigService

    payload = AlgorithmDashboardConfigTestRequest(
        host="192.168.1.242",
        port=3306,
        username="kaifa",
        password_plain="secret",
        database_name="hn_kongguan",
    )

    with patch(
        "app.services.algorithm_dashboard._dashboard_engine",
        side_effect=OperationalError(
            "SELECT 1",
            {},
            Exception(
                "(2013, 'Lost connection to MySQL server during query')"
            ),
        ),
    ):
        result = AlgorithmDashboardConfigService.test_connection(payload)

    assert result.success is False
    assert result.message == "MySQL 连接测试失败，请检查主机、端口、网络连通性或 MySQL 服务状态"


def test_algorithm_dashboard_config_access_denied_mentions_host_grant():
    from app.schemas.algorithm_dashboard import AlgorithmDashboardConfigTestRequest
    from app.services.algorithm_dashboard import AlgorithmDashboardConfigService

    payload = AlgorithmDashboardConfigTestRequest(
        host="192.168.1.242",
        port=3306,
        username="kaifa",
        password_plain="secret",
        database_name="hn_kongguan",
    )

    with patch(
        "app.services.algorithm_dashboard._dashboard_engine",
        side_effect=OperationalError(
            "SELECT 1",
            {},
            Exception(
                "(1045, \"Access denied for user 'kaifa'@'192.168.3.26' (using password: YES)\")"
            ),
        ),
    ):
        result = AlgorithmDashboardConfigService.test_connection(payload)

    assert result.success is False
    assert result.message == "MySQL 连接测试失败，请检查账号、密码或主机授权是否正确"


def test_algorithm_dashboard_database_url_keeps_real_password():
    from app.services.algorithm_dashboard import _database_url

    database_url = _database_url(
        host="192.168.1.242",
        port=6523,
        username="kaifa",
        password="rayshon.com",
        database_name="hn_kongguan",
    )

    assert "rayshon.com" in database_url
    assert "***" not in database_url
