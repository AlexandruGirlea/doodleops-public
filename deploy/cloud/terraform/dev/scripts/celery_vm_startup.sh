#!/bin/bash
set -xe

touch /etc/WEB_APP_VARIABLES.env

echo "MYSQL_HOST=\"${MYSQL_HOST}\"" >> /etc/WEB_APP_VARIABLES.env
echo "REDIS_HOST=\"${REDIS_HOST}\"" >> /etc/WEB_APP_VARIABLES.env
echo "GCP_PROJECT_ID=${GCP_PROJECT_ID}" >> /etc/WEB_APP_VARIABLES.env

if [ ${VM_NAME} = 'dev_celery_worker_vm' ]; then
    echo 'ENV_MODE="dev_celery_worker"' >> /etc/WEB_APP_VARIABLES.env
elif [ ${VM_NAME} = 'dev_celery_beat_vm' ]; then
    echo 'ENV_MODE="dev_celery_beat"' >> /etc/WEB_APP_VARIABLES.env
else
    echo "VM_NAME is not recognised, it is set to: ${VM_NAME}"
fi
logger -p user.info "Secrets file created."

source /etc/WEB_APP_VARIABLES.env

# Ensure Docker is running
while ! systemctl is-active --quiet docker; do
  echo "Waiting for Docker to start..."
  sleep 1
done

docker run --rm -v /etc:/secrets google/cloud-sdk:slim \
  sh -c "gcloud secrets versions access latest --secret='app-celery-service-account-key' --project=$GCP_PROJECT_ID --format='get(payload.data)' | base64 --decode > /secrets/service_account_key.json"

docker rmi google/cloud-sdk:slim
