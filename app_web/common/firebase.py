import logging
from typing import Tuple

import requests
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.contrib.auth.hashers import check_password
from firebase_admin import auth as fb_auth
from firebase_admin.exceptions import FirebaseError
from firebase_admin.auth import (
    ExpiredIdTokenError,
    RevokedIdTokenError,
    InvalidIdTokenError,
)

from app_users.models import CustomUser
from common.auth import validate_password
from common.exceptions import CustomRequestException, CustomValidationError

logger = logging.getLogger(__name__)


def verify_id_token(id_token: str) -> str:
    try:
        decoded_token = fb_auth.verify_id_token(id_token, check_revoked=True)
        return decoded_token.get("uid")
    except (
        InvalidIdTokenError,
        RevokedIdTokenError,
        ExpiredIdTokenError,
        Exception,
    ) as e:
        logger.exception(e)


def get_jwt_token(email: str, password: str) -> Tuple[str, str]:
    resp = requests.post(
        settings.GCP_JWT_AUTH_URL,
        headers={"content-type": "application/json; charset=UTF-8"},
        json={"email": email, "password": password, "returnSecureToken": True},
    )
    jwt_token = resp.json().get("idToken")
    refresh_token = resp.json().get("refreshToken")
    if resp.status_code != 200 or not jwt_token:
        logger.error(
            "Error logging in user: %s. Status code: %s. Response: %s",
            email,
            resp.status_code,
            resp.json(),
        )
        raise PermissionDenied("There was an error logging in")
    return jwt_token, refresh_token


def delete_user_based_on_credentials(email: str, password: str) -> None:
    try:
        fb_auth.get_user_by_email(email)
    except fb_auth.UserNotFoundError:
        return

    jwt_token, _ = get_jwt_token(email, password)
    resp = requests.post(
        url=settings.FB_ACCOUNT_DELETE_URL,
        headers={"content-type": "application/json; charset=UTF-8"},
        json={"idToken": jwt_token},
    )
    if resp.status_code != 200:
        raise CustomRequestException(
            "There was an error deleting the user",
            http_status_code=resp.status_code,
        )


def delete_user_based_on_uid(username: str) -> None:
    try:
        fb_auth.delete_user(uid=username)
    except fb_auth.UserNotFoundError:
        raise CustomRequestException(
            "There was an error deleting the user",
            http_status_code=404,
        )


def update_user_password(
    user_obj: CustomUser, password: str, new_password1: str, new_password2: str
) -> bool:
    if not check_password(password, user_obj.password):
        raise CustomValidationError(
            dict_errors={"password": "The current password is not valid."},
        )

    validate_password(password1=new_password1, password2=new_password2)

    try:
        user = fb_auth.get_user_by_email(user_obj.email)
        jwt_token, _ = get_jwt_token(user_obj.email, password)

        if not verify_id_token(jwt_token) == user.uid:
            logger.error("Invalid token provided for user: %s", user_obj.email)
            raise ValueError("The old password is not valid.")

        fb_auth.update_user(user.uid, password=new_password1)

    except fb_auth.UserNotFoundError as e:
        logger.exception(
            "User not found %s password. If error persists, please contact "
            "support.",
            user_obj.email,
        )
        raise CustomRequestException(
            "There was an error updating the user password",
            http_status_code=404,
        ) from e

    except FirebaseError as e:
        logger.exception(
            "Firebase error while updating user %s password: %s",
            user_obj.email,
            e,
        )
        raise CustomRequestException(
            "There was an error updating the user password",
            http_status_code=400,
        ) from e

    except Exception as e:
        logger.exception(e)
        raise CustomRequestException(
            "There was an error updating the user password",
            http_status_code=400,
        ) from e

    else:
        logger.info(
            "User password updated successfully for user: %s", user_obj.email
        )
        return True
