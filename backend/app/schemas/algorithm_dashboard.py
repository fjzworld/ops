from datetime import datetime, timedelta
from typing import List, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator


DEFAULT_TIMEZONE = "Asia/Shanghai"
MAX_RANGE_DAYS = 31


class AlgorithmRuntimeWindow(BaseModel):
    month: str
    from_time: datetime
    to_time: datetime
    timezone: str


class AlgorithmRuntimeQuery(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    month: str = Field(..., pattern=r"^\d{6}$")
    from_time: str = Field(default="now-3h", alias="from")
    to_time: str = Field(default="now", alias="to")
    timezone: str = DEFAULT_TIMEZONE

    @field_validator("month")
    @classmethod
    def validate_month(cls, value: str) -> str:
        month = int(value[4:6])
        if month < 1 or month > 12:
            raise ValueError("月份必须是有效的 YYYYMM")
        return value

    def resolve_window(self, now: Optional[datetime] = None) -> AlgorithmRuntimeWindow:
        zone_name = DEFAULT_TIMEZONE if self.timezone == "browser" else self.timezone
        try:
            zone = ZoneInfo(zone_name)
        except ZoneInfoNotFoundError as exc:
            raise ValueError("timezone 无效") from exc

        current = now or datetime.now(zone)
        if current.tzinfo is None:
            current = current.replace(tzinfo=zone)
        else:
            current = current.astimezone(zone)

        start = _parse_time_expr(self.from_time, current, zone)
        end = _parse_time_expr(self.to_time, current, zone)

        if start >= end:
            raise ValueError("开始时间必须早于结束时间")
        if end - start > timedelta(days=MAX_RANGE_DAYS):
            raise ValueError(f"时间范围不能超过 {MAX_RANGE_DAYS} 天")

        return AlgorithmRuntimeWindow(
            month=self.month,
            from_time=start,
            to_time=end,
            timezone=zone_name,
        )


class AlgorithmSeriesPoint(BaseModel):
    time: datetime
    value: Optional[float] = None


class AlgorithmPanelSeries(BaseModel):
    name: str
    display_name: str
    points: List[AlgorithmSeriesPoint]


class AlgorithmDashboardPanel(BaseModel):
    key: str
    title: str
    panel_type: str
    unit: str
    series: List[AlgorithmPanelSeries]


class AlgorithmRuntimeDashboardResponse(BaseModel):
    title: str
    month: str
    from_time: datetime
    to_time: datetime
    timezone: str
    refresh_seconds: int
    panels: List[AlgorithmDashboardPanel]


class AlgorithmDashboardMonthsResponse(BaseModel):
    months: List[str]


class AlgorithmDashboardConfigRead(BaseModel):
    configured: bool = True
    name: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    database_name: Optional[str] = None
    enabled: bool = False
    has_password: bool = False


class AlgorithmDashboardConfigUpdate(BaseModel):
    name: str
    host: str
    port: int = Field(..., ge=1, le=65535)
    username: str
    password_plain: Optional[str] = None
    database_name: str
    enabled: bool = True


class AlgorithmDashboardConfigTestRequest(BaseModel):
    host: str
    port: int = Field(..., ge=1, le=65535)
    username: str
    password_plain: str
    database_name: str


class AlgorithmDashboardConfigTestResult(BaseModel):
    success: bool
    message: str


def _parse_time_expr(value: str, now: datetime, zone: ZoneInfo) -> datetime:
    if value == "now":
        return now

    if value.startswith("now-"):
        amount = value[4:-1]
        unit = value[-1]
        if not amount.isdigit() or unit not in {"m", "h", "d"}:
            raise ValueError("时间表达式无效")
        delta_value = int(amount)
        if unit == "m":
            return now - timedelta(minutes=delta_value)
        if unit == "h":
            return now - timedelta(hours=delta_value)
        return now - timedelta(days=delta_value)

    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError("时间格式无效") from exc

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=zone)
    return parsed.astimezone(zone)
