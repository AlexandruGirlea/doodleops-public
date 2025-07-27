import logging
from typing import Union

from celery import shared_task, group

from app_api.models import APICounter
from common.redis_logic.redis_utils import build_user_credits_used_dict
from common.redis_logic.redis_schemas import (
    REDIS_KEY_CREDITS_USED_PER_API_ENDPOINT_BY_USER,
)
from common.other import chunked
from common.date_time_utils import (
    get_dates_in_range,
    get_current_date_time,
    convert_date_str_to_date,
    get_previous_day_date_as_str,
    get_previous_date_based_on_number_of_days,
    convert_date_to_str,
)


logger = logging.getLogger(__name__)


@shared_task
def has_api_counter_discrepancies(
    username: str = "",
) -> bool:
    """
    This will loop through all the Redis keys and APICounter objects and
    look for discrepancies. It will return a True/False if there are any.

    It will look only at the records of the past 5 days, excluding current
    day and previous day (5 - 2 = 3days). This is because the cronjob that runs
    every 3 hours will update the records for the previous day.

    This task will run every day at 02:00.

    It will also log any errors it finds. If we want to fix them manually, we
    can run the `manual_store_api_counter_obj_for_billing_period` task by
    providing the username and the billing period we want to recalculate based on
    Redis.
    """

    found_errors = False

    redis_key_name = REDIS_KEY_CREDITS_USED_PER_API_ENDPOINT_BY_USER.split(":")[0]
    start_date = get_previous_date_based_on_number_of_days(days_back=5)
    end_date = get_previous_date_based_on_number_of_days(days_back=2)

    dates_in_range = get_dates_in_range(
        start_date=start_date,
        end_date=end_date,
    )

    string_dates = list(map(convert_date_to_str, dates_in_range))

    redis_data_dict = {}
    for str_date in string_dates:
        redis_key_pattern = redis_key_name + f":{str_date}:*"

        if username:
            redis_key_pattern = redis_key_pattern.replace("*", f":{username}:*")

        redis_data_dict = build_user_credits_used_dict(redis_key_pattern)

    for k, v in redis_data_dict.items():
        date_str, username, api_name = k.split(":")
        credits_used, number_of_calls = v

        try:
            api_counter_obj = APICounter.objects.get(
                date=convert_date_str_to_date(date_str),
                username=username,
                api_name=api_name,
            )
            if (
                credits_used != api_counter_obj.credits_used
                or number_of_calls != api_counter_obj.number_of_calls
            ):
                logger.error(
                    f"Discrepancy found for APICounter object: {api_counter_obj}. "
                    f"Redis value: {v}."
                )
                found_errors = True

        except APICounter.DoesNotExist:
            logger.error(
                f"APICounter object not found for date: {date_str}, "
                f"username: {username}, api_name: {api_name}. "
                f"Redis value: {v}."
            )
            found_errors = True
        except APICounter.MultipleObjectsReturned:
            logger.error(
                f"Multiple APICounter objects returned for date: {date_str}, "
                f"username: {username}, api_name: {api_name}. "
                f"Redis value: {v}, Redis key: {k}."
            )
            found_errors = True

    return found_errors


def manual_store_api_counter_obj_for_billing_period(
    username: str = "",
    start_date_str: str = "",
    end_date_str: str = "",
) -> Union[str, bool]:
    """
    This is meant to be run manually in case we find log error discrepancies.
    This will take the data from Redis and store it in the database (APICounter).
    """
    redis_key_name = REDIS_KEY_CREDITS_USED_PER_API_ENDPOINT_BY_USER.split(":")[0]
    try:
        start_date = convert_date_str_to_date(start_date_str)
        end_date = convert_date_str_to_date(end_date_str)
    except ValueError:
        return "Invalid date format."

    if start_date > end_date:
        return "Start date cannot be greater than end date."
    elif end_date == get_current_date_time(get_date=True):
        return "You cannot run this task for the current day."
    elif end_date > get_current_date_time(get_date=True):
        return "You cannot run this task for a future date."

    dates_in_range = get_dates_in_range(
        start_date=start_date,
        end_date=end_date,
    )

    string_dates = list(map(convert_date_to_str, dates_in_range))

    redis_data_dict = {}

    for str_date in string_dates:
        redis_key_pattern = redis_key_name + f":{str_date}:{username}:*"

        redis_data_dict = build_user_credits_used_dict(redis_key_pattern)

    for k, v in redis_data_dict.items():
        date_str, username, api_name = k.split(":")
        credits_used, number_of_calls = v

        try:
            api_counter_obj = APICounter.objects.get(
                date=convert_date_str_to_date(date_str),
                username=username,
                api_name=api_name,
            )
            if (
                credits_used != api_counter_obj.credits_used
                or number_of_calls != api_counter_obj.number_of_calls
            ):
                api_counter_obj.credits_used = credits_used
                api_counter_obj.number_of_calls = number_of_calls
                api_counter_obj.save()
        except APICounter.DoesNotExist:
            api_counter_obj = APICounter(
                date=convert_date_str_to_date(date_str),
                username=username,
                api_name=api_name,
                credits_used=credits_used,
                number_of_calls=number_of_calls,
            )
            api_counter_obj.save()
        except APICounter.MultipleObjectsReturned:
            logger.error(
                f"Multiple APICounter objects returned for date: {date_str}, "
                f"username: {username}, api_name: {api_name}. "
                f"Redis value: {v}, Redis key: {k}."
            )
            APICounter.objects.filter(
                date=convert_date_str_to_date(date_str),
                username=username,
                api_name=api_name,
            ).delete()

            api_counter_obj = APICounter(
                date=convert_date_str_to_date(date_str),
                username=username,
                api_name=api_name,
                credits_used=credits_used,
                number_of_calls=number_of_calls,
            )
            api_counter_obj.save()


@shared_task
def cronjob_store_api_counter_obj_for_the_previous_day(
    username: str = "",
) -> bool:
    """
    If username, it will only execute for that user, otherwise it will execute
    for all users.

    This function will set the number of credits used per user per api endpoint
    for the previous day. It will be called by a cronjob every 3 hours.

    The info in APICounter will be used both for displaying the user's usage in
    the profile page and for metering the user's usage.

    For more details see: `send_subscription_item_metered_usage_to_stripe`.
    """
    previous_day = get_previous_day_date_as_str()
    redis_key_pattern = (
        REDIS_KEY_CREDITS_USED_PER_API_ENDPOINT_BY_USER.split(":")[0]
        + f":{previous_day}:*"
    )
    if username:
        redis_key_pattern = redis_key_pattern.replace("*", f":{username}:*")
    
    # {"{date_str}:{username}:{api_name}": [credits_used, number_of_calls]}
    redis_data_dict = build_user_credits_used_dict(redis_key_pattern)

    existing_api_counters = []
    api_counters_to_create = []

    for k, v in redis_data_dict.items():
        date_str, username, api_name = k.split(":")
        credits_used, number_of_calls = v

        try:
            api_counter_obj = APICounter.objects.get(
                date=convert_date_str_to_date(date_str),
                username=username,
                api_name=api_name,
            )
            if credits_used != api_counter_obj.credits_used:
                api_counter_obj.credits_used = credits_used
                api_counter_obj.number_of_calls = number_of_calls
                existing_api_counters.append(api_counter_obj)
        except APICounter.DoesNotExist:
            api_counter_obj = {
                "date": convert_date_str_to_date(date_str),
                "username": username,
                "api_name": api_name,
                "credits_used": credits_used,
                "number_of_calls": number_of_calls,
            }
            api_counters_to_create.append(api_counter_obj)
        except APICounter.MultipleObjectsReturned:
            logger.error(
                f"Multiple APICounter objects returned for date: {date_str}, "
                f"username: {username}, api_name: {api_name}. "
                f"Redis value: {v}, Redis key: {k}."
            )
            APICounter.objects.filter(
                date=convert_date_str_to_date(date_str),
                username=username,
                api_name=api_name,
            ).delete()

            api_counter_obj = {
                "date": convert_date_str_to_date(date_str),
                "username": username,
                "api_name": api_name,
                "credits_used": credits_used,
                "number_of_calls": number_of_calls,
            }
            api_counters_to_create.append(api_counter_obj)

    existing_api_counters_batches = chunked(existing_api_counters, 100)
    group(
        batch_update_create_api_counter_objects.s(batch, existing=True)
        for batch in existing_api_counters_batches
    ).apply_async()

    api_counters_to_create_batches = chunked(api_counters_to_create, 100)
    group(
        batch_update_create_api_counter_objects.s(batch, existing=False)
        for batch in api_counters_to_create_batches
    ).apply_async()

    return True


@shared_task
def batch_update_create_api_counter_objects(
    batch: list[dict],
    existing: bool = False,
) -> None:
    mock_api_counter_objs = [APICounter(**dict_obj) for dict_obj in batch]

    if existing:
        APICounter.objects.bulk_update(
            objs=mock_api_counter_objs,
            fields=["number_of_calls", "credits_used"],
        )
    else:
        APICounter.objects.bulk_create(mock_api_counter_objs)
