from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from app.config import settings

try:
    LOCAL_TZ = ZoneInfo(settings.timezone)
except Exception:  # noqa: BLE001
    LOCAL_TZ = ZoneInfo("UTC")

UTC = timezone.utc


def now_utc() -> datetime:
    return datetime.now(UTC)


def parse_local_dt(value: str | None) -> datetime | None:
    """Parse an HTML datetime-local string (naive, local tz) into aware UTC."""
    if not value:
        return None
    value = value.strip()
    if not value:
        return None
    # datetime-local can be "YYYY-MM-DDTHH:MM" or with seconds
    for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%S"):
        try:
            naive = datetime.strptime(value, fmt)
            break
        except ValueError:
            continue
    else:
        return None
    return naive.replace(tzinfo=LOCAL_TZ).astimezone(UTC)


def to_local_input(value: datetime | None) -> str:
    """Format an aware/naive datetime for an HTML datetime-local input value."""
    if value is None:
        return ""
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(LOCAL_TZ).strftime("%Y-%m-%dT%H:%M")
