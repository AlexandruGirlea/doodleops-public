import json
import logging
from http import HTTPStatus

import redis
from fastapi import HTTPException, responses, Response

from core import settings
from common.redis_utils import (
    get_api_cost,
    log_api_call,
    update_user_credits,
    check_if_user_has_enough_credits,
    check_if_user_has_metered_subscription,
    check_if_user_has_exceeded_daily_api_call_limit,
    log_credits_used_per_api_endpoint_by_user,
)

logger = logging.getLogger(__name__)

GENERIC_ERROR_MSG = (
    "Something went wrong. If the problem persists, please contact support."
)


async def cost_setup(
    redis_conn: redis.Redis, username: str, api_name: str, current_date: str
) -> tuple[int, bool]:
    try:
        api_cost = await get_api_cost(
            redis_conn=redis_conn,
            api_name=api_name,
        )
    except redis.exceptions.ConnectionError as e:
        logger.error(
            f"Redis connection error when trying to get API cost for API "
            f"`{api_name}`, requested by user {username}. Error: {e}"
        )

        raise HTTPException(
            status_code=500,
            detail="Internal server error.",
        ) from e

    if not api_cost:
        logger.error(
            f"API cost not found for API `{api_name}`, "
            f"requested by user {username}."
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "There was an error processing your request. If the problem "
                "persists, please contact support."
                ),
        )

    await check_if_user_has_exceeded_daily_api_call_limit(
        redis_conn=redis_conn,
        username=username,
        current_date=current_date,
    )

    is_metered = await check_if_user_has_metered_subscription(
        redis_conn=redis_conn,
        username=username,
    )

    if not is_metered:
        await check_if_user_has_enough_credits(
            redis_conn=redis_conn,
            username=username,
            api_cost=api_cost,
        )

    return api_cost, is_metered


async def cost_teardown(
    redis_conn: redis.Redis,
    resp_type: str,
    resp: Response,
    username: str,
    api_name: str,
    api_cost: int,
    current_date: str,
    timestamp: int,
    is_metered: bool = False,
):
    """
    Returns responses if they are 200 or 400. If other status codes are returned,
    logs the error and raises an 500 exception.
    """
    if resp_type not in {"file", "str", "json"}:
        logger.error(
        f"Expected response type to be 'file', 'str' or 'json', got {resp_type}."
        )
        raise HTTPException(
            status_code=500,
            detail="Internal server error.",
        )

    if not resp or not isinstance(resp, Response):
        # no need to take credit from the user, this is our logic error
        logger.error(
            f"Expected response to be FastAPI Response object, got {type(resp)}."
        )
        raise HTTPException(
            status_code=500,
            detail="Internal server error.",
        )

    if resp.status_code == HTTPStatus.BAD_REQUEST.value:
        api_cost = settings.API_COST_BAD_REQUEST

    if resp.status_code in (HTTPStatus.OK.value, HTTPStatus.BAD_REQUEST.value):
        if not is_metered:
            await update_user_credits(
                username=username,
                redis_conn=redis_conn,
                api_cost=api_cost,
            )

        await log_credits_used_per_api_endpoint_by_user(
            redis_conn=redis_conn,
            username=username,
            api_name=api_name,
            api_cost=api_cost,
            current_date=current_date,
            timestamp=timestamp,
        )

    # it does not matter if the API call was successful or not, we still log
    # the API call to limit abuse.
    await log_api_call(
        redis_conn=redis_conn,
        current_date=current_date,
        username=username,
        api_name=api_name,
        timestamp=timestamp,
        success=resp.status_code == HTTPStatus.OK.value,
    )

    if resp.status_code == HTTPStatus.OK.value:
        return resp
    elif resp.status_code == HTTPStatus.BAD_REQUEST.value:
        return responses.JSONResponse(
            status_code=HTTPStatus.BAD_REQUEST.value,
            content=json.loads(resp.body.decode()),
        )

    # if we are here, something went wrong
    err_msg = (
        f"User {username} encounter an error when calling GCF API: {api_name} at "
        f"timestamp: {timestamp}. "
        f"Resp status code {resp.status_code}."
    )
    if resp_type == "file":
        err_msg += f" Response: {resp.body}."

    logging.error(err_msg)

    raise HTTPException(
        status_code=HTTPStatus.INTERNAL_SERVER_ERROR.value,
        detail=GENERIC_ERROR_MSG
    )


async def free_api_call(
    redis_conn: redis.Redis,
    resp_type: str,
    resp: Response,
    username: str,
    api_name: str,
    current_date: str,
    timestamp: int,
):
    """
    This is used for free API calls, like get more info for api calls
    """
    if resp_type not in {"list", "str", "json"}:
        logger.error(
        f"Expected response type to be 'list', 'str' or 'json', got {resp_type}."
        )
        raise HTTPException(
            status_code=500,
            detail=GENERIC_ERROR_MSG
        )

    if not resp or not isinstance(resp, Response):
        # no need to take credit from the user, this is our logic error
        logger.error(
            f"Expected response to be FastAPI Response object, got {type(resp)}."
        )
        raise HTTPException(
            status_code=500,
            detail=GENERIC_ERROR_MSG
        )

    await log_api_call(
        redis_conn=redis_conn,
        current_date=current_date,
        username=username,
        api_name=api_name,
        timestamp=timestamp,
        success=True,
    )

    if resp.status_code == HTTPStatus.OK.value:
        return resp
    elif resp.status_code == HTTPStatus.BAD_REQUEST.value:
        return responses.JSONResponse(
            status_code=HTTPStatus.BAD_REQUEST.value,
            content=json.loads(resp.body.decode()),
        )

    err_msg = (
        f"User {username} encounter an error when calling GCF API: {api_name} at "
        f"timestamp: {timestamp}. "
        f"Resp status code {resp.status_code}."
    )

    logging.error(err_msg)

    raise HTTPException(
        status_code=HTTPStatus.INTERNAL_SERVER_ERROR.value,
        detail=GENERIC_ERROR_MSG
    )
