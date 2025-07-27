import logging
from datetime import datetime

from sqlalchemy.orm import Session
from fastapi import HTTPException, Depends, Request
from cryptography.fernet import Fernet, InvalidToken
from twilio.request_validator import RequestValidator

from core import settings
from common.sql_utils import get_db_conn
from common.redis_utils import get_redis_conn
from schemas.auth import TokenData
from schemas.sql_db import DjangoSession, AuthUser
from schemas.redis_db import (
    REDIS_KEY_USER_GENERATED_TOKEN, REDIS_OPENAI_OAUTH_USER_GENERATED_TOKEN
)


logger = logging.getLogger("APP_API_"+__name__)
fernet_cipher = Fernet(settings.CRYPT_SECRET_KEY_WEB)


async def verify_token(
    req: Request,
    redis_conn=Depends(get_redis_conn),
    db: Session = Depends(get_db_conn)
) -> TokenData:
    try:
        if not req.headers.get("Authorization"):
            raise HTTPException(
                status_code=401, detail="Missing Authorization header"
            )
        elif req.headers["Authorization"].count(" ") != 1:
            raise HTTPException(
                status_code=401, detail="Invalid Authorization header format"
            )

        token_type, token = req.headers["Authorization"].split(" ")

        if token_type.lower() != "bearer":
            logger.error(f"Invalid token type, not bearer: {token_type}")
            raise HTTPException(status_code=401, detail="Invalid token type")

        username = await redis_conn.get(
            REDIS_KEY_USER_GENERATED_TOKEN.format(token=token)
        )
        if username:
            return TokenData(
                access_token=token,
                username=username.decode(),
                generated_by="user",
                ttl=await redis_conn.ttl(token),
            )

        # openai oauth token
        username = await redis_conn.get(
            REDIS_OPENAI_OAUTH_USER_GENERATED_TOKEN.format(token=token)
        )

        if username:
            return TokenData(
                access_token=token,
                username=username.decode(),
                generated_by="openai_oauth",
                ttl=await redis_conn.ttl(token),
            )

        # session_key:username
        session_key, username = (
            fernet_cipher.decrypt(token.encode()).decode().split(":")
        )

        db_session = (
            db.query(DjangoSession)
            .filter(DjangoSession.session_key == session_key)
            .first()
        )
        if db_session.expire_date < datetime.utcnow():
            raise HTTPException(status_code=403, detail="Session has expired")

        db_user = db.query(AuthUser).filter(AuthUser.username == username).first()

        if not all([db_session, db_user]):
            raise HTTPException(status_code=404, detail="User not found")

    except ValueError:
        raise HTTPException(
            status_code=401, detail="Invalid Authorization header format"
        )

    except InvalidToken:
        raise HTTPException(status_code=401, detail="Invalid token")

    else:
        return TokenData(
            access_token=token,
            username=username,
            generated_by="system",
            ttl=None,
        )

validator = RequestValidator(settings.TWILIO_AUTH_TOKEN)


async def verify_twilio_whatsapp(req: Request) -> str:
    """If auth successful, returns the sender's phone number."""
    if settings.ENV_MODE == "local":
        return "+1234567890"
    try:
        url = str(req.url).replace("http://", "https://")
        body = await req.form()
        post_params = dict(body)
        signature = req.headers.get("X-Twilio-Signature")

        if not validator.validate(url, post_params, signature):
            raise HTTPException(
                status_code=403,
                detail="Forbidden",
            )

        sender_phone_number = post_params.get("From")
        if not sender_phone_number.startswith("whatsapp:"):
            raise HTTPException(
                status_code=400,
                detail="Invalid phone number",
            )

        if not any(
            sender_phone_number.startswith("whatsapp:"+country_code)
            for country_code in settings.COUNTRY_CODE_PHONE_RESTRICTION.split(",")
        ):
            raise HTTPException(
                status_code=400,
                detail="Country code not supported yet.",
            )

        return sender_phone_number.replace("whatsapp:", "")
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal Server Error",
        )
