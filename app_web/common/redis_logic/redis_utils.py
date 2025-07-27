import logging

from django.db.models import Sum

from app_api.models import APICounter
from app_users.models import CustomUser
from app_financial.models import (
    CustomerCreditsBought,
    StripeSubscriptionItem,
)
from common.redis_logic.custom_redis import RedisClient, set_redis_key
from common.redis_logic.redis_schemas import (
    REDIS_KEY_USER_CREDIT_BOUGHT,
    REDIS_KEY_USER_API_DAILY_CALL_LIMIT,
    REDIS_KEY_METERED_SUBSCRIPTION_USERS,
    REDIS_KEY_CREDITS_USED_PER_API_ENDPOINT_BY_USER,
    REDIS_KEY_SUBSCRIPTIONS_MONTHLY_CREDIT_REMAINING,
    REDIS_KEY_USER_HAS_ACTIVE_SUBSCRIPTION,
)
from common.date_time_utils import (
    get_current_date_time,
    get_current_date_as_str,
    convert_date_str_to_date,
    convert_date_to_str,
)
from common.other import convert_cents_into_credit

logger = logging.getLogger(__name__)


def add_one_time_credits_to_customer(
    user_obj: CustomUser,
    amount_in_cents: int,
    details: str = "stripe",
    added_manually: bool = False,
) -> int:
    """
    Returns the number of credits added to the user.
    """
    no_of_credits = convert_cents_into_credit(
        amount_in_cents=amount_in_cents,
        credit_type="one_time",
        added_manually=added_manually
    )
    cred_bought_obj = CustomerCreditsBought.objects.create(
        user=user_obj,
        credits=no_of_credits,
        details=details,
    )

    set_redis_key(
        key=REDIS_KEY_USER_CREDIT_BOUGHT.format(
            username=user_obj.username,
            id=cred_bought_obj.id,
        ),
        simple_value=no_of_credits,
    )
    return no_of_credits


def set_credits_for_customer_subscription(
    username: str,
    api_daily_call_limit: int,
    credits_monthly: int = None,
):
    """
    If credits_monthly is None => it's a metered subscription
    """
    set_redis_key(
        key=REDIS_KEY_USER_API_DAILY_CALL_LIMIT.format(username=username),
        simple_value=api_daily_call_limit,
    )

    if credits_monthly:
        set_redis_key(
            key=REDIS_KEY_SUBSCRIPTIONS_MONTHLY_CREDIT_REMAINING.format(
                username=username
            ),
            simple_value=credits_monthly,
        )
    else:
        set_redis_key(
            key=REDIS_KEY_METERED_SUBSCRIPTION_USERS.format(username=username),
            simple_value=1,
        )


def get_remaining_credits_bought(username: str) -> dict:
    """
    This function will return the number of credits a user has remaining from
    their credit bought directly.
    """
    key_pattern = REDIS_KEY_USER_CREDIT_BOUGHT.format(
        username=username,
        id="*",
    )

    total_credits = {}
    customer_credits_bought_pks = []
    with RedisClient() as client:
        for key in client.scan_iter(match=key_pattern):
            pk = int(key.decode("utf-8").split(":")[-1])
            customer_credits_bought_pks.append(pk)
            credit_value = client.get(key)
            if credit_value is not None:
                total_credits[pk] = int(credit_value)

    return total_credits


def get_remaining_monthly_subscription_credits(username: str) -> int:
    """
    This function will return the number of credits a user has remaining for the
    month. This is based on their subscription plan.
    """
    key = REDIS_KEY_SUBSCRIPTIONS_MONTHLY_CREDIT_REMAINING.format(
        username=username
    )
    with RedisClient() as client:
        credit_value = client.get(key)
        if credit_value is not None:
            return int(credit_value)
    return 0


def get_user_api_usage_for_current_day(
    username: str,
):
    """This is not for sending data to Stripe, it's for the user's dashboard."""
    date_str = get_current_date_as_str()
    redis_key_pattern = (
        REDIS_KEY_CREDITS_USED_PER_API_ENDPOINT_BY_USER.split(":")[0]
        + f":{date_str}:{username}:*"
    )

    redis_data_dict = build_user_credits_used_dict(redis_key_pattern)

    if APICounter.objects.filter(
        username=username,
        date=convert_date_str_to_date(date_str),
    ).exists():
        logger.error("There are already API counters for today.")

    mock_counters = []
    for k, v in redis_data_dict.items():
        date_str, username, api_name = k.split(":")
        credits_used, number_of_calls = v
        mock_counters.append(
            APICounter(
                username=username,
                api_name=api_name,
                credits_used=credits_used,
                number_of_calls=number_of_calls,
                date=convert_date_str_to_date(date_str),
            )
        )

    return mock_counters


def get_credits_used_dynamically(
    date: str,
    username: str,
    before_timestamp: int = None,
    after_timestamp: int = None,
) -> int:
    """
    If before_timestamp and after_timestamp are none, it will return the
    total credits used for the given date.
    """

    total_credits = 0
    with RedisClient() as client:
        base_key_pattern = (
            REDIS_KEY_CREDITS_USED_PER_API_ENDPOINT_BY_USER.replace(
                ":{api_name}:{timestamp}:{random_char}", ":*"
            ).format(
                date=date,
                username=username,
            )
        )
        
        list_of_keys = []
        while True:
            cursor, keys = client.scan(match=base_key_pattern, count=1000)

            for k in keys:
                k = k.decode("utf-8") if isinstance(k, bytes) else k

                timestamp = int(k.split(":")[-2])

                if (
                    (  # check if the timestamp is within the range
                        before_timestamp and after_timestamp
                        and after_timestamp <= timestamp <= before_timestamp
                    )
                    or (before_timestamp and timestamp <= before_timestamp)
                    or (after_timestamp and after_timestamp <= timestamp)
                    or (not before_timestamp and not after_timestamp)
                ):
                    list_of_keys.append(k)

            if cursor == 0:
                break
        
        if list_of_keys:
            pipeline = client.pipeline()
            for k in list_of_keys:
                pipeline.get(k)
            results = pipeline.execute()
            
            if results:
                total_credits = sum(int(x) for x in results)
                
    return total_credits


def build_user_credits_used_dict(redis_key_pattern: str) -> dict[str, list[int]]:
    """
    Returns: {"{date_str}:{username}:{api_name}": [credits_used, number_of_calls]}
    """
    redis_data_dict = {}
    with RedisClient() as client:
        cursor = 0
        while True:
            cursor, keys = client.scan(  # scan for the matching pattern
                cursor, match=redis_key_pattern, count=1000
            )
            if keys:
                pipeline = client.pipeline()
                for key in keys:
                    pipeline.get(key)
                results = pipeline.execute()  # batch the GET commands
                
                # Process the keys and their corresponding results
                for key, value in zip(keys, results):
                    if isinstance(key, bytes):  # convert to string
                        key = key.decode("utf-8")
                    if key.count(":") != 5:  # check the format
                        logger.error(
                            f"Redis key `{key}` does not have the correct format."
                        )
                        continue
                    
                    parts = key.split(":")
                    date_str = parts[1]
                    username = parts[2]
                    api_name = parts[3]
                    simple_key = f"{date_str}:{username}:{api_name}"
                    
                    # Convert the retrieved value to an integer for credits_used
                    credits_used = int(value)
                    
                    if simple_key in redis_data_dict:
                        redis_data_dict[simple_key][0] += credits_used
                        redis_data_dict[simple_key][1] += 1
                    else:
                        redis_data_dict[simple_key] = [credits_used, 1]
            
            # When the cursor returns 0, the scan is complete
            if cursor == 0:
                break
    
    return redis_data_dict


def get_credits_used_per_metered_subscription_item(
    subs_item_obj: StripeSubscriptionItem,
) -> int:
    """
    This function will return the total credits used for a metered subscription
    from start_date to end_date of the subscription.
    """
    username = subs_item_obj.user.username

    counter_objs = APICounter.objects.filter(
        username=username,
        date__gt=subs_item_obj.start_date,
        date__lt=subs_item_obj.end_date,
    )

    current_date = get_current_date_time(get_date=True)

    current_period_start_credits = get_credits_used_dynamically(
        date=convert_date_to_str(subs_item_obj.start_date),
        username=username,
        after_timestamp=subs_item_obj.current_period_start,
    )

    current_period_end_credits = get_credits_used_dynamically(
        date=convert_date_to_str(subs_item_obj.end_date),
        username=username,
        before_timestamp=subs_item_obj.current_period_end,
    )

    if counter_objs:
        quantity = int(counter_objs.aggregate(total=Sum("credits_used"))["total"])
    else:
        quantity = 0
    quantity += current_period_start_credits + current_period_end_credits

    if subs_item_obj.start_date < current_date < subs_item_obj.end_date:
        # if the subscription is active, we add the current day's usage
        quantity += get_credits_used_dynamically(
            date=convert_date_to_str(current_date),
            username=username,
        )

    return quantity


def calculate_metered_cost_based_on_tier(
    subs_item_obj: StripeSubscriptionItem,
) -> tuple[int, int]:
    """Return cost_in_cents, credits_used."""
    if not subs_item_obj:
        logger.error("No subscription item provided.")
        raise ValueError("No subscription item provided.")
    elif not subs_item_obj.pricing_plan.is_metered:
        logger.error(
            "This is not a metered subscription."
            f"Subscription ID: {subs_item_obj.id}"
        )
        raise ValueError("This is not a metered subscription.")

    credits_used = get_credits_used_per_metered_subscription_item(
        subs_item_obj=subs_item_obj,
    )

    if not credits_used:
        return 0, 0

    # get the price tiers for the subscription_item
    tiers = subs_item_obj.pricing_plan.pricing_plan_tiers.all().order_by("start")

    # get the price tier for the current credits used
    usage_tier = None
    for tier in tiers:
        if tier.start <= credits_used:
            usage_tier = tier
        else:
            break

    if not usage_tier:
        return 0, 0

    cost = (
            (credits_used * usage_tier.price_in_cents) +
            usage_tier.flat_amount_in_cents
    )

    return cost, credits_used


def get_instant_cost_in_dollars_for_metered_subscription(
    subs_item_obj: StripeSubscriptionItem,
) -> float:
    """
    We get partial info from SQL, and the rest from Redis. We base our estimate
    on Start and End date of StripeSubscriptionItem and on the
    PricingBuySubscriptionTier model.
    """
    if not subs_item_obj:
        logger.error("No subscription item provided.")
        raise ValueError("No subscription item provided.")
    elif not subs_item_obj.pricing_plan.is_metered:
        logger.error(
            "This is not a metered subscription."
            f"Subscription ID: {subs_item_obj.id}"
        )
        raise ValueError("This is not a metered subscription.")
    elif not subs_item_obj.is_active:
        logger.error(
            "This is not an active subscription."
            f"Subscription ID: {subs_item_obj.id}"
        )
        raise ValueError("This is not an active subscription.")

    username = subs_item_obj.user.username

    # SQL. This should only contain data until the current day.
    current_date = get_current_date_time(get_date=True)

    if subs_item_obj.start_date > current_date:
        logger.error(
            "Subscription item start date is in the future."
            f"Subscription ID: {subs_item_obj.id}"
        )
        raise ValueError("Subscription item start date is in the future.")

    elif subs_item_obj.start_date == current_date:
        if APICounter.objects.filter(
            username=username,
            date=current_date,
        ).exists():
            logger.error(
                "Subscription item start date is today and there are already"
                " API counters for today."
                f"Subscription ID: {subs_item_obj.id}"
            )
            raise ValueError("There is already data recorded for today.")

    cost, credits_used = calculate_metered_cost_based_on_tier(
        subs_item_obj=subs_item_obj,
    )

    return cost / 100  # convert to dollars


def set_user_subscription_false(username: str):
    set_redis_key(
        key=REDIS_KEY_USER_HAS_ACTIVE_SUBSCRIPTION.format(username=username),
        simple_value=0,
    )


def set_user_subscription_active(username: str):
    set_redis_key(
        key=REDIS_KEY_USER_HAS_ACTIVE_SUBSCRIPTION.format(username=username),
        simple_value=1,
    )


def remove_credits_bought_directly(username: str, no_of_credits: int):
    if not no_of_credits or no_of_credits <= 0:
        msg = "Number of credits to remove must be a positive number."
        logger.error(msg)
        raise ValueError(msg)

    total_credits_bought = get_remaining_credits_bought(username=username)
    if no_of_credits >= sum(total_credits_bought.values()):
        msg = (
            "Number of credits to remove is greater than the total credits "
            "bought directly."
        )
        logger.error(msg)
        raise ValueError(msg)

    key_pattern = REDIS_KEY_USER_CREDIT_BOUGHT.format(username=username, id="*")

    with RedisClient() as client:
        for key in client.scan_iter(match=key_pattern):
            credit_value = int(client.get(key))
            if no_of_credits >= credit_value:
                no_of_credits -= credit_value
                client.delete(key)
            else:
                client.set(key, credit_value - no_of_credits)
                break


def remove_credits_bought_using_subscription(username: str, no_of_credits: int):
    if not no_of_credits or no_of_credits <= 0:
        msg = "Number of credits to remove must be a positive number."
        logger.error(msg)
        raise ValueError(msg)

    total_credits_subscription = get_remaining_monthly_subscription_credits(
        username=username
    )
    if no_of_credits >= total_credits_subscription:
        msg = (
            "Number of credits to remove is greater than the total credits from "
            "the subscription."
        )
        logger.error(msg)
        raise ValueError(msg)

    set_redis_key(
        key=REDIS_KEY_SUBSCRIPTIONS_MONTHLY_CREDIT_REMAINING.format(
            username=username
        ),
        simple_value=total_credits_subscription - no_of_credits,
    )
