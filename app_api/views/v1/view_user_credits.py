import logging

from fastapi import Depends
from fastapi.responses import JSONResponse

from schemas.auth import TokenData
from access_management.api_auth import verify_token
from common.redis_utils import get_redis_conn
from views.urls import default_urls
from views.v1.route import v1_default_view_router
from common.redis_utils import (
	sum_user_credits_bought,
	check_if_user_has_metered_subscription,
)
from schemas.redis_db import (
	REDIS_KEY_USER_HAS_ACTIVE_SUBSCRIPTION,
	REDIS_KEY_SUBSCRIPTIONS_MONTHLY_CREDIT_REMAINING,
)


logger = logging.getLogger("APP_API_DEFAULT"+__name__)


@v1_default_view_router.get(
	default_urls["view_user_credits_v1"].api_url, include_in_schema=True,
	description="View the remaining credits for the user.",
)
async def view_user_credits(
		token_data: TokenData = Depends(verify_token),
		redis_conn=Depends(get_redis_conn),
):
	username = token_data.username
	is_metered = await check_if_user_has_metered_subscription(
		redis_conn=redis_conn,
		username=username,
	)

	if not is_metered:
		credits_bought_remaining = await sum_user_credits_bought(
			redis_conn=redis_conn,
			username=username,
		)
		has_active_sub = await redis_conn.get(
			REDIS_KEY_USER_HAS_ACTIVE_SUBSCRIPTION.format(username=username)
		)

		has_active_sub = int(has_active_sub.decode()) if has_active_sub else 0

		if has_active_sub:
			subscriptions_monthly_credit_remaining = await redis_conn.get(
				REDIS_KEY_SUBSCRIPTIONS_MONTHLY_CREDIT_REMAINING.format(
					username=username
				)
			)
			subscriptions_monthly_credit_remaining = (
				int(subscriptions_monthly_credit_remaining.decode())
				if subscriptions_monthly_credit_remaining
				else 0
			)
		else:
			subscriptions_monthly_credit_remaining = 0

		user_credits = (
				subscriptions_monthly_credit_remaining + credits_bought_remaining
		)
		return JSONResponse(
			status_code=200,
			content={
				"user_credits": f"You have {user_credits} credits remaining."
			}
		)
	else:
		return JSONResponse(
			status_code=200,
			content={
				"user_credits": (
					"You have an Enterprise subscription. To find out the "
					"estimated cost for this month, please visit your "
					"DoodleOps dashboard at: "
					"https://doodleops.com/dev/profile/general/"
				)
			}
		)
