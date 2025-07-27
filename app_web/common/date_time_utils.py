from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from django.utils import timezone


DATE_STR_FORMAT = "%d-%m-%Y"
ADMIN_CREATED_FORMAT = "%Y-%m-%d %H:%M:%S.%f"


def get_current_date_time(get_date: bool = False) -> datetime.date:
    if not get_date:
        return timezone.now()
    return timezone.now().date()


def get_current_year() -> int:
    return get_current_date_time().year


def get_current_date_as_str() -> str:
    return get_current_date_time(get_date=True).strftime(DATE_STR_FORMAT)


def get_beginning_of_current_day_timestamp() -> int:
    return int(
        timezone.now()
        .replace(hour=0, minute=0, second=0, microsecond=0)
        .timestamp()
    )


def get_current_timestamp() -> int:
    return int(timezone.now().timestamp())


def get_previous_day_date() -> datetime.date:
    return get_current_date_time(get_date=True) - timedelta(days=1)


def get_previous_date_based_on_number_of_days(days_back: int) -> datetime.date:
    return get_current_date_time(get_date=True) - timedelta(days=days_back)


def get_previous_day_date_as_str() -> str:
    return get_previous_day_date().strftime(DATE_STR_FORMAT)


def get_previous_day_timestamp() -> int:
    previous_day = get_current_date_time(get_date=True) - timedelta(days=1)
    previous_day_start = previous_day.replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return int(previous_day_start.timestamp())


def convert_timestamp_to_beginning_of_day_timestamp(
    timestamp: int,
) -> int:
    aware_dt = timezone.make_aware(datetime.fromtimestamp(timestamp))
    start_of_day = aware_dt.replace(hour=0, minute=0, second=0, microsecond=0)
    return int(start_of_day.timestamp())


def convert_date_str_to_date(date_str: str) -> datetime.date:
    """
    DateField in Django is not timezone aware.
    """
    return datetime.strptime(date_str, DATE_STR_FORMAT).date()


def convert_date_to_str(date: datetime.date) -> str:
    """
    DateField in Django is not timezone aware.
    """
    return date.strftime(DATE_STR_FORMAT)


def convert_timestamp_to_date(timestamp: int) -> datetime.date:
    """
    DateField in Django is not timezone aware.
    """
    return datetime.fromtimestamp(timestamp).date()


def convert_timestamp_to_datetime(timestamp: int) -> datetime:
    """
    This function takes in a timestamp and returns a datetime object
    using Django's timezone.
    """
    return timezone.make_aware(datetime.fromtimestamp(timestamp))


def get_dates_in_range(
    start_date: datetime.date, end_date: datetime.date
) -> list[datetime.date]:
    return [
        start_date + timedelta(days=x)
        for x in range((end_date - start_date).days + 1)
    ]


def get_date_time_for_one_year_back(get_date: bool = False):
    """
    Calculate the date/time for one year back
    """
    resp = timezone.now() - relativedelta(years=1)
    if not get_date:
        return resp
    return resp.date()


def get_date_time_for_specified_hours_ago(hours: int, get_date: bool = False):
    """
    Calculate the date/time for specified hours ago
    """
    resp = timezone.now() - timedelta(hours=hours)
    if not get_date:
        return resp
    return resp.date()
