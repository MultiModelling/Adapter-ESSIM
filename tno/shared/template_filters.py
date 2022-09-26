import pprint
from datetime import datetime, timedelta, timezone

import pytz

from tno.shared.log import get_logger

logger = get_logger(__name__)


def _to_local_tz(utc_dt: datetime):
    return utc_dt.replace(tzinfo=timezone.utc).astimezone(
        tz=pytz.timezone("Europe/Amsterdam")
    )


def format_date(value: datetime):
    return _to_local_tz(value).strftime("%Y-%m-%d") if value else "-"


def format_datetime(value: datetime):
    return _to_local_tz(value).strftime("%Y-%m-%d %H:%M:%S") if value else "-"


def format_duration(value: timedelta):
    # Strip off milliseconds.
    return str(value).rpartition(".")[0]


def format_yesno_bool(value: bool):
    return "Ja" if value else "No"


def format_pprint(value):
    return pprint.pformat(value)
