import os
import json
import logging

from google.cloud import secretmanager
from fastapi import HTTPException, Request
from cryptography.fernet import Fernet, InvalidToken


logger = logging.getLogger("APP_PDF_V1_"+__name__)


if os.getenv("ENV_MODE") != "local":
    # get secrets using GCP Service Account from Secret Manager
    project_id = os.getenv("GCP_PROJECT_ID")
    if not project_id:
        msg = "GCP_PROJECT_ID not set"
        logger.error(msg)
        raise ValueError(msg)
    secret_name = f"projects/{project_id}/secrets/app-api-apps/versions/latest"

    client = secretmanager.SecretManagerServiceClient()
    response = client.access_secret_version(request={"name": secret_name})

    if response.payload.data:
        secrets_json = json.loads(response.payload.data.decode('UTF-8'))
        for k, v in secrets_json.items():
            os.environ[k] = str(v)
    else:
        msg = "No data found in secret"
        logger.error(msg)
        raise ValueError(msg)

FERNET_CIPHER = Fernet(os.environ.get("CRYPT_SECRET_KEY_G_CLOUD_RUN"))
EXPECTED_TOKEN_CLOUD_RUN = os.environ.get("EXPECTED_TOKEN_CLOUD_RUN")


async def verify_token(req: Request) -> bool:
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

    try:
        if (
                EXPECTED_TOKEN_CLOUD_RUN == FERNET_CIPHER.decrypt(
                                                token.encode()
                                            ).decode()
        ):
            return True
        else:
            raise HTTPException(
                status_code=401, detail="Access denied"
            )

    except ValueError:
        raise HTTPException(
            status_code=401, detail="Invalid Authorization header format"
        )

    except InvalidToken:
        raise HTTPException(status_code=401, detail="Invalid token")

    except Exception as e:
        logger.exception("Error while verifying token %s", e)
        raise HTTPException(
            status_code=401, detail="Access denied"
        )
