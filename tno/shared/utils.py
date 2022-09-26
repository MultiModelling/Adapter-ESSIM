import time

from functools import wraps
from typing import Tuple
from datetime import date, datetime, timedelta

from tno.shared.log import get_logger

logger = get_logger(__name__)


def year_to_datetimes(year: int) -> Tuple[datetime, datetime]:
    """Convert a year number to start and end of year datetimes.

    Args:
        year: [description]
    """
    year_start = date(year, 1, 1)
    year_start_dt = datetime.combine(year_start, datetime.min.time())
    year_end = date(year + 1, 1, 1) - timedelta(days=1)
    year_end_dt = datetime.combine(year_end, datetime.max.time())
    return year_start_dt, year_end_dt


def is_leap_year(year: int) -> bool:
    """Determine whether the input year is a leap year, or not.

    Args:
        year (int): The year for which to determine whether or not it is a leap year.
    """
    if (year % 4) == 0:
        if (year % 100) == 0:
            if (year % 400) == 0:
                return True
            else:
                return False
        else:
            return True
    else:
        return False


def timed(func):
    """This decorator prints the execution time for the decorated function."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        runtime = round(end - start, 2)
        logger.debug(
            "{} ran in {}s".format(func.__name__, runtime),
            function=func.__name__,
            runtime=runtime,
        )
        return result

    return wrapper
