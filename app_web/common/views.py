from http import HTTPStatus

from django.http import JsonResponse

from common.redis_logic.custom_redis import set_redis_key, get_redis_key
from common.redis_logic.redis_schemas import REDIS_KEY_USER_DJANGO_CALL_RATE_LIMIT
from common.date_time_utils import get_current_timestamp


def rate_limit(rate=5):
    """
    Decorator to enforce a rate limit on a view.

    `rate`: Number of seconds to wait between requests.

    It limits the request a user can make to a view decorated by this function
    """

    def decorator(view_func):
        def _wrapped_view(request, *args, **kwargs):
            # Check if the user is authenticated
            if not request.user.is_authenticated:
                return JsonResponse(
                    {"error": "User not authenticated"},
                    status=HTTPStatus.UNAUTHORIZED.value,
                )

            key = REDIS_KEY_USER_DJANGO_CALL_RATE_LIMIT.format(
                username=request.user.username
            )

            last_request = get_redis_key(key=key)

            timestamp = get_current_timestamp()

            if (
                last_request
                and last_request.isdigit()
                and (timestamp - int(last_request)) < rate
            ):
                # Too many requests
                return JsonResponse(
                    {"error": "Rate limit exceeded"},
                    status=HTTPStatus.TOO_MANY_REQUESTS.value,
                )

            # Update the last request time
            set_redis_key(key=key, simple_value=timestamp)

            # Proceed with the request
            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator
