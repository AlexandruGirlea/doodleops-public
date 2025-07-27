import os
import logging

import google.auth.transport.requests
import google.oauth2.id_token
from fastapi import HTTPException, Request

from core.settings import EVENTARC_SERVICE_ACCOUNT


logger = logging.getLogger("APP_AI_V1_"+__name__)


async def verify_auth(req: Request) -> bool:
    """Check if the request is made by the Eventarc service account."""
    if os.getenv("ENV_MODE") == "local":
        return True

    if not req.headers.get("Authorization"):
        raise HTTPException(
            status_code=401, detail="Missing Authorization header"
        )

    try:
        token_type, token = req.headers.get("Authorization").split(" ")
    except ValueError as e:
        logger.exception("Error while splitting Authorization header %s", e)
        raise HTTPException(
            status_code=401, detail="Invalid Authorization header format"
        )

    if token_type.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid token type")

    request_adapter = google.auth.transport.requests.Request()
    try:
        claims = google.oauth2.id_token.verify_oauth2_token(
            token, request_adapter
        )
    except Exception as e:
        logger.exception("Error while verifying token %s", e)
        raise HTTPException(
            status_code=401, detail="Access denied"
        )

    if claims.get("email") != EVENTARC_SERVICE_ACCOUNT:
        raise HTTPException(
            status_code=401, detail="Access denied"
        )

    return True
