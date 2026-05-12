from datetime import datetime

import pytest
from pydantic import ValidationError
from sqlalchemy.exc import OperationalError

from app.core.exceptions import BadRequestException
from app.schemas.algorithm_dashboard import AlgorithmRuntimeQuery
from app.services.algorithm_dashboard import (
    AlgorithmDashboardService,
    ResolvedDashboardConfig,
)


def test_algorithm_runtime_query_accepts_valid_month_and_relative_range():
    query = AlgorithmRuntimeQuery(
        month="202409",
        from_time="now-3h",
        to_time="now",
        timezone="Asia/Shanghai",
    )

    window = query.resolve_window(now=datetime(2024, 9, 10, 12, 0, 0))

    assert window.month == "202409"
    assert window.from_time.isoformat() == "2024-09-10T09:00:00+08:00"
    assert window.to_time.isoformat() == "2024-09-10T12:00:00+08:00"


@pytest.mark.parametrize(
    "month",
    [
        "2024 OR 1=1",
        "202413",
        "2024-09",
        "202409;DROP TABLE algorithm_runtime",
    ],
)
def test_algorithm_runtime_query_rejects_unsafe_month(month):
    with pytest.raises(ValidationError):
        AlgorithmRuntimeQuery(
            month=month,
            from_time="now-3h",
            to_time="now",
            timezone="Asia/Shanghai",
        )


def test_algorithm_runtime_query_rejects_invalid_time_window():
    query = AlgorithmRuntimeQuery(
        month="202409",
        from_time="2024-09-10T12:00:00+08:00",
        to_time="2024-09-10T09:00:00+08:00",
        timezone="Asia/Shanghai",
    )

    with pytest.raises(ValueError, match="开始时间必须早于结束时间"):
        query.resolve_window()


def test_algorithm_runtime_query_rejects_overlong_time_window():
    query = AlgorithmRuntimeQuery(
        month="202409",
        from_time="2024-09-01T00:00:00+08:00",
        to_time="2024-10-10T00:00:00+08:00",
        timezone="Asia/Shanghai",
    )

    with pytest.raises(ValueError, match="时间范围不能超过"):
        query.resolve_window()


def test_algorithm_dashboard_service_uses_bound_parameters_only():
    query = AlgorithmRuntimeQuery(
        month="202409",
        from_time="2024-09-10T09:00:00+08:00",
        to_time="2024-09-10T12:00:00+08:00",
        timezone="Asia/Shanghai",
    )
    window = query.resolve_window()

    definitions = AlgorithmDashboardService.panel_definitions()

    assert definitions
    for panel in definitions:
        sql = panel.sql_for(window)
        assert f"_{window.month}" in sql
        assert window.from_time.isoformat() not in sql
        assert window.to_time.isoformat() not in sql
        assert ":from_time" in sql
        assert ":to_time" in sql
        assert panel.params(window)["month"] == "202409"


def test_algorithm_dashboard_months_connection_error_is_sanitized():
    config = ResolvedDashboardConfig(
        name="海南空管",
        host="192.168.1.242",
        port=6523,
        username="kaifa",
        password_plain="secret",
        database_name="hn_kongguan",
        enabled=True,
    )

    with pytest.raises(
        BadRequestException,
        match="算法看板数据源连接失败，请检查账号、密码或主机授权是否正确",
    ):
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(
                "app.services.algorithm_dashboard.AlgorithmDashboardConfigService.get_required_config",
                lambda: config,
            )
            mp.setattr(
                "app.services.algorithm_dashboard._dashboard_engine",
                lambda *_: (_ for _ in ()).throw(
                    OperationalError(
                        "SELECT 1",
                        {},
                        Exception(
                            "(1045, \"Access denied for user 'kaifa'@'192.168.3.26' (using password: YES)\")"
                        ),
                    )
                ),
            )
            AlgorithmDashboardService.list_months()


def test_algorithm_dashboard_query_connection_error_is_sanitized():
    query = AlgorithmRuntimeQuery(
        month="202409",
        from_time="2024-09-10T09:00:00+08:00",
        to_time="2024-09-10T12:00:00+08:00",
        timezone="Asia/Shanghai",
    )
    config = ResolvedDashboardConfig(
        name="海南空管",
        host="192.168.1.242",
        port=6523,
        username="kaifa",
        password_plain="secret",
        database_name="hn_kongguan",
        enabled=True,
    )

    with pytest.raises(
        BadRequestException,
        match="算法看板数据源连接失败，请检查账号、密码或主机授权是否正确",
    ):
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(
                "app.services.algorithm_dashboard.AlgorithmDashboardConfigService.get_required_config",
                lambda: config,
            )
            mp.setattr(
                "app.services.algorithm_dashboard._dashboard_engine",
                lambda *_: (_ for _ in ()).throw(
                    OperationalError(
                        "SELECT 1",
                        {},
                        Exception(
                            "(1045, \"Access denied for user 'kaifa'@'192.168.3.26' (using password: YES)\")"
                        ),
                    )
                ),
            )
            AlgorithmDashboardService.fetch_algorithm_runtime(query)
