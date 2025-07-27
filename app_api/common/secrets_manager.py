import os
import json
import logging

from google.cloud import secretmanager

logger = logging.getLogger(__name__)


def set_app_api_secrets() -> None:
    if os.getenv("ENV_MODE") == "local":
        return

    project_id = os.getenv("GCP_PROJECT_ID")

    if not project_id:
        msg = "GCP_PROJECT_ID not set"
        logger.error(msg)
        raise ValueError(msg)

    for app_name in ["app-api", "app-common"]:
        secret_name = f"projects/{project_id}/secrets/{app_name}/versions/latest"

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
