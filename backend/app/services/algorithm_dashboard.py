import logging
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from typing import Dict, Iterable, List

from sqlalchemy import select, text
from sqlalchemy.engine import Engine
from sqlalchemy.engine.url import URL
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError

from app.core.database import SessionLocal
from app.core.encryption import decrypt_string, encrypt_string
from app.core.exceptions import BadRequestException, InternalServerError
from app.models.algorithm_dashboard_config import AlgorithmDashboardConfig
from app.schemas.algorithm_dashboard import (
    AlgorithmDashboardConfigRead,
    AlgorithmDashboardConfigTestRequest,
    AlgorithmDashboardConfigTestResult,
    AlgorithmDashboardConfigUpdate,
    AlgorithmDashboardMonthsResponse,
    AlgorithmDashboardPanel,
    AlgorithmPanelSeries,
    AlgorithmRuntimeDashboardResponse,
    AlgorithmRuntimeQuery,
    AlgorithmRuntimeWindow,
    AlgorithmSeriesPoint,
)

logger = logging.getLogger(__name__)


ALGORITHM_DISPLAY_NAMES = {
    "radar_wind": "合成风",
    "vortex_fuse": "旋涡组网",
    "x_awr_wind": "反演风场",
    "x_coord_transform": "坐标转换",
    "x_dec_radar": "雷达基数据解析",
    "x_etop_ebot": "回波顶高底高",
    "x_fuse": "融合组网",
    "x_max_dbz": "组合回波",
    "x_meso_cyclone": "中气旋",
    "x_phase_identi": "相态识别",
    "x_qpe": "qpe",
    "x_qpf": "qpf",
    "x_rainfall": "累计雨量",
    "x_storm_extrapolate": "风暴外推",
    "x_storm_recognition": "风暴识别",
    "x_storm_trace": "风暴追踪",
    "x_tvs": "tvs",
    "x_vad": "vad",
    "x_vil": "vil",
    "x_vtk": "三维等值面",
}


@dataclass(frozen=True)
class PanelDefinition:
    key: str
    title: str
    panel_type: str
    unit: str
    sql_template: str

    def sql_for(self, window: AlgorithmRuntimeWindow) -> str:
        return self.sql_template.format(month=window.month)

    def params(self, window: AlgorithmRuntimeWindow) -> Dict[str, object]:
        return {
            "month": window.month,
            "from_time": _to_mysql_datetime(window.from_time),
            "to_time": _to_mysql_datetime(window.to_time),
            "bucket_seconds": _bucket_seconds(window.from_time, window.to_time),
        }


@dataclass(frozen=True)
class ResolvedDashboardConfig:
    name: str
    host: str
    port: int
    username: str
    password_plain: str
    database_name: str
    enabled: bool

    @property
    def cache_key(self) -> str:
        return _database_url(
            host=self.host,
            port=self.port,
            username=self.username,
            password=self.password_plain,
            database_name=self.database_name,
        )


class AlgorithmDashboardConfigService:
    @staticmethod
    def get_config(db) -> AlgorithmDashboardConfig | None:
        return db.execute(
            select(AlgorithmDashboardConfig).order_by(AlgorithmDashboardConfig.id.asc())
        ).scalars().first()

    @staticmethod
    async def get_config_async(db: AsyncSession) -> AlgorithmDashboardConfigRead:
        result = await db.execute(
            select(AlgorithmDashboardConfig).order_by(AlgorithmDashboardConfig.id.asc())
        )
        config = result.scalars().first()
        if not config:
            return AlgorithmDashboardConfigRead(configured=False)

        return AlgorithmDashboardConfigRead(
            configured=True,
            name=config.name,
            host=config.host,
            port=config.port,
            username=config.username,
            database_name=config.database_name,
            enabled=config.enabled,
            has_password=bool(config.password_enc),
        )

    @staticmethod
    def upsert_config(db, payload: AlgorithmDashboardConfigUpdate) -> AlgorithmDashboardConfig:
        config = AlgorithmDashboardConfigService.get_config(db)
        if not config:
            if not payload.password_plain:
                raise BadRequestException(message="首次配置时必须填写密码")
            config = AlgorithmDashboardConfig()
            db.add(config)

        if payload.password_plain:
            config.password_enc = encrypt_string(payload.password_plain)
        elif not config.password_enc:
            raise BadRequestException(message="请提供 MySQL 密码")

        config.name = payload.name.strip()
        config.host = payload.host.strip()
        config.port = payload.port
        config.username = payload.username.strip()
        config.database_name = payload.database_name.strip()
        config.enabled = payload.enabled

        db.commit()
        db.refresh(config)
        return config

    @staticmethod
    async def upsert_config_async(
        db: AsyncSession, payload: AlgorithmDashboardConfigUpdate
    ) -> AlgorithmDashboardConfigRead:
        result = await db.execute(
            select(AlgorithmDashboardConfig).order_by(AlgorithmDashboardConfig.id.asc())
        )
        config = result.scalars().first()
        if not config:
            if not payload.password_plain:
                raise BadRequestException(message="首次配置时必须填写密码")
            config = AlgorithmDashboardConfig()
            db.add(config)

        if payload.password_plain:
            config.password_enc = encrypt_string(payload.password_plain)
        elif not config.password_enc:
            raise BadRequestException(message="请提供 MySQL 密码")

        config.name = payload.name.strip()
        config.host = payload.host.strip()
        config.port = payload.port
        config.username = payload.username.strip()
        config.database_name = payload.database_name.strip()
        config.enabled = payload.enabled

        await db.commit()
        await db.refresh(config)
        return AlgorithmDashboardConfigRead(
            configured=True,
            name=config.name,
            host=config.host,
            port=config.port,
            username=config.username,
            database_name=config.database_name,
            enabled=config.enabled,
            has_password=bool(config.password_enc),
        )

    @staticmethod
    def get_required_config() -> ResolvedDashboardConfig:
        session = SessionLocal()
        try:
            config = AlgorithmDashboardConfigService.get_config(session)
            if not config or not config.enabled:
                raise BadRequestException(message="算法看板数据源未配置")

            password_plain = decrypt_string(config.password_enc or "")
            if not password_plain:
                raise BadRequestException(message="算法看板数据源密码无效")

            return ResolvedDashboardConfig(
                name=config.name,
                host=config.host,
                port=config.port,
                username=config.username,
                password_plain=password_plain,
                database_name=config.database_name,
                enabled=config.enabled,
            )
        finally:
            session.close()

    @staticmethod
    def test_connection(
        payload: AlgorithmDashboardConfigTestRequest,
    ) -> AlgorithmDashboardConfigTestResult:
        try:
            engine = _dashboard_engine(
                _database_url(
                    host=payload.host,
                    port=payload.port,
                    username=payload.username,
                    password=payload.password_plain,
                    database_name=payload.database_name,
                )
            )
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return AlgorithmDashboardConfigTestResult(
                success=True,
                message="MySQL 连接测试成功",
            )
        except Exception as exc:
            logger.exception("Algorithm dashboard config connection test failed")
            return AlgorithmDashboardConfigTestResult(
                success=False,
                message=_friendly_connection_error_message(exc),
            )


class AlgorithmDashboardService:
    @staticmethod
    def panel_definitions() -> List[PanelDefinition]:
        return [
            PanelDefinition(
                key="product_delay",
                title="各产品延迟时间监控",
                panel_type="timeseries",
                unit="秒",
                sql_template="""
                    SELECT
                      product_module AS series_name,
                      FROM_UNIXTIME(FLOOR(UNIX_TIMESTAMP(data_time) / :bucket_seconds) * :bucket_seconds) AS bucket_time,
                      AVG(TIMESTAMPDIFF(SECOND, data_time, product_time)) AS value
                    FROM product_time_{month}
                    WHERE data_time >= :from_time AND data_time <= :to_time
                    GROUP BY product_module, bucket_time
                    ORDER BY bucket_time
                """,
            ),
            PanelDefinition(
                key="algorithm_runtime",
                title="算法运行时间监控",
                panel_type="timeseries",
                unit="秒",
                sql_template="""
                    SELECT
                      algorithm_type AS series_name,
                      FROM_UNIXTIME(FLOOR(UNIX_TIMESTAMP(data_time) / :bucket_seconds) * :bucket_seconds) AS bucket_time,
                      AVG(run_time) AS value
                    FROM algorithm_monitor_{month}
                    WHERE data_time >= :from_time AND data_time <= :to_time
                    GROUP BY algorithm_type, bucket_time
                    ORDER BY bucket_time
                """,
            ),
            PanelDefinition(
                key="basic_data_delay",
                title="基础数据延迟时间监控",
                panel_type="timeseries",
                unit="秒",
                sql_template="""
                    SELECT
                      CONCAT(t1.radar_name, '(', t1.radar_id, ')') AS series_name,
                      FROM_UNIXTIME(FLOOR(UNIX_TIMESTAMP(t2.data_time) / :bucket_seconds) * :bucket_seconds) AS bucket_time,
                      AVG(TIMESTAMPDIFF(SECOND, t2.data_time, t2.download_time)) AS value
                    FROM radar_config t1
                    LEFT JOIN basic_data_time_{month} t2 ON t1.radar_id = t2.data_id
                    WHERE t2.data_time >= :from_time AND t2.data_time <= :to_time
                    GROUP BY series_name, bucket_time
                    ORDER BY bucket_time
                """,
            ),
            PanelDefinition(
                key="basic_data_integrity",
                title="基础数据完整性监控",
                panel_type="status-history",
                unit="秒",
                sql_template="""
                    SELECT
                      CONCAT(t1.radar_name, '(', t1.radar_id, ')') AS series_name,
                      FROM_UNIXTIME(FLOOR(UNIX_TIMESTAMP(t2.data_time) / :bucket_seconds) * :bucket_seconds) AS bucket_time,
                      AVG(TIMESTAMPDIFF(SECOND, t2.data_time, t2.download_time)) AS value
                    FROM radar_config t1
                    LEFT JOIN basic_data_time_{month} t2 ON t1.radar_id = t2.data_id
                    WHERE t2.data_time >= :from_time AND t2.data_time <= :to_time
                    GROUP BY series_name, bucket_time
                    ORDER BY bucket_time
                """,
            ),
            PanelDefinition(
                key="algorithm_status_history",
                title="算法运行状态监控",
                panel_type="status-history",
                unit="状态",
                sql_template="""
                    SELECT
                      CONCAT(algorithm_type, data_id) AS series_name,
                      FROM_UNIXTIME(FLOOR(UNIX_TIMESTAMP(data_time) / :bucket_seconds) * :bucket_seconds) AS bucket_time,
                      AVG(status) AS value
                    FROM algorithm_monitor_{month}
                    WHERE data_time >= :from_time AND data_time <= :to_time
                    GROUP BY series_name, bucket_time
                    ORDER BY bucket_time
                """,
            ),
            PanelDefinition(
                key="algorithm_status_trend",
                title="算法运行状态趋势",
                panel_type="timeseries",
                unit="状态",
                sql_template="""
                    SELECT
                      CONCAT(algorithm_type, data_id) AS series_name,
                      FROM_UNIXTIME(FLOOR(UNIX_TIMESTAMP(data_time) / :bucket_seconds) * :bucket_seconds) AS bucket_time,
                      AVG(status) AS value
                    FROM algorithm_monitor_{month}
                    WHERE data_time >= :from_time AND data_time <= :to_time
                    GROUP BY series_name, bucket_time
                    ORDER BY bucket_time
                """,
            ),
        ]

    @classmethod
    def fetch_algorithm_runtime(
        cls, query: AlgorithmRuntimeQuery
    ) -> AlgorithmRuntimeDashboardResponse:
        window = query.resolve_window()
        config = AlgorithmDashboardConfigService.get_required_config()
        panels: List[AlgorithmDashboardPanel] = []

        try:
            engine = _dashboard_engine(config.cache_key)
            with engine.connect() as conn:
                for definition in cls.panel_definitions():
                    rows = conn.execute(
                        text(definition.sql_for(window)), definition.params(window)
                    ).mappings()
                    panels.append(cls._build_panel(definition, rows))
        except BadRequestException:
            raise
        except Exception as exc:
            logger.exception("Algorithm dashboard query failed")
            _raise_dashboard_query_exception(exc, "算法看板数据查询失败")

        return AlgorithmRuntimeDashboardResponse(
            title=config.name,
            month=window.month,
            from_time=window.from_time,
            to_time=window.to_time,
            timezone=window.timezone,
            refresh_seconds=5,
            panels=panels,
        )

    @staticmethod
    def list_months() -> AlgorithmDashboardMonthsResponse:
        config = AlgorithmDashboardConfigService.get_required_config()
        try:
            engine = _dashboard_engine(config.cache_key)
            with engine.connect() as conn:
                rows = conn.execute(
                    text(
                        """
                        SELECT REPLACE(TABLE_NAME, 'product_time_', '') AS month
                        FROM information_schema.TABLES
                        WHERE TABLE_SCHEMA = COALESCE(NULLIF(:schema_name, ''), DATABASE())
                          AND TABLE_NAME REGEXP '^product_time_[0-9]{6}$'
                          AND TABLE_ROWS > 0
                        ORDER BY month DESC
                        LIMIT 36
                        """
                    ),
                    {"schema_name": config.database_name},
                ).mappings()
                return AlgorithmDashboardMonthsResponse(
                    months=[str(row["month"]) for row in rows]
                )
        except BadRequestException:
            raise
        except Exception as exc:
            logger.exception("Algorithm dashboard month query failed")
            _raise_dashboard_query_exception(exc, "算法看板月份查询失败")

    @classmethod
    def _build_panel(
        cls, definition: PanelDefinition, rows: Iterable[Dict[str, object]]
    ) -> AlgorithmDashboardPanel:
        grouped: Dict[str, List[AlgorithmSeriesPoint]] = {}
        for row in rows:
            series_name = str(row["series_name"])
            grouped.setdefault(series_name, []).append(
                AlgorithmSeriesPoint(
                    time=row["bucket_time"],
                    value=_float_or_none(row["value"]),
                )
            )

        series = [
            AlgorithmPanelSeries(
                name=name,
                display_name=cls._display_name(name),
                points=points,
            )
            for name, points in grouped.items()
        ]
        return AlgorithmDashboardPanel(
            key=definition.key,
            title=definition.title,
            panel_type=definition.panel_type,
            unit=definition.unit,
            series=series,
        )

    @staticmethod
    def _display_name(name: str) -> str:
        for raw_name, display_name in ALGORITHM_DISPLAY_NAMES.items():
            if raw_name in name:
                return name.replace(raw_name, display_name)
        return name


@lru_cache
def _dashboard_engine(database_url: str) -> Engine:
    if not database_url:
        raise BadRequestException(message="算法看板数据源未配置")
    return create_engine(
        database_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        pool_recycle=1800,
        pool_timeout=10,
        echo=False,
    )


def _bucket_seconds(from_time: datetime, to_time: datetime) -> int:
    total_seconds = max(int((to_time - from_time).total_seconds()), 60)
    target_points = 720
    bucket = int(total_seconds / target_points / 60) * 60
    return max(60, bucket)


def _to_mysql_datetime(value: datetime) -> datetime:
    return value.replace(tzinfo=None)


def _float_or_none(value: object) -> float | None:
    if value is None:
        return None
    return float(value)


def _friendly_connection_error_message(exc: Exception) -> str:
    if isinstance(exc, OperationalError):
        detail = str(exc).lower()
        if "access denied" in detail:
            return "MySQL 连接测试失败，请检查账号、密码或主机授权是否正确"
        if "unknown database" in detail:
            return "MySQL 连接测试失败，请检查数据库名是否正确"
        if "lost connection" in detail or "can't connect" in detail:
            return "MySQL 连接测试失败，请检查主机、端口、网络连通性或 MySQL 服务状态"
        return "MySQL 连接测试失败，请检查数据源配置和网络连通性"
    return "MySQL 连接测试失败，请稍后重试"


def _database_url(
    host: str,
    port: int,
    username: str,
    password: str,
    database_name: str,
) -> str:
    return URL.create(
        "mysql+pymysql",
        username=username,
        password=password,
        host=host,
        port=port,
        database=database_name,
        query={"charset": "utf8mb4"},
    ).render_as_string(hide_password=False)


def _friendly_dashboard_error_message(exc: Exception) -> str:
    connection_message = _friendly_connection_error_message(exc)
    if connection_message.startswith("MySQL 连接测试失败"):
        return connection_message.replace("MySQL 连接测试失败", "算法看板数据源连接失败", 1)
    return "算法看板数据源连接失败，请稍后重试"


def _raise_dashboard_query_exception(exc: Exception, default_message: str) -> None:
    if isinstance(exc, OperationalError):
        raise BadRequestException(message=_friendly_dashboard_error_message(exc)) from exc
    raise InternalServerError(message=default_message) from exc
