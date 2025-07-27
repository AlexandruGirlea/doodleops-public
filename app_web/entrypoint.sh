#!/bin/bash
# stopping the execution at the first sign of trouble
set -e
echo "Running with ENV_MODE set to: $ENV_MODE"
printenv

# Function to check if required environment variables are set
check_env_vars() {
    local missing_vars=0
    for var in "$@"; do
        if [ -z "${!var}" ]; then
            echo "Error: $var environment variable is not set." >&2
            missing_vars=$((missing_vars + 1))
        fi
    done
    if [ $missing_vars -ne 0 ]; then
      echo "Error: $missing_vars required environment variables are not set. Exiting..." >&2
      exit 1
    fi
}

# List of required environment variables
required_vars=(
"ENV_MODE" "GCP_PROJECT_ID" "MYSQL_HOST" "REDIS_HOST"
)

# Check required environment variables
check_env_vars "${required_vars[@]}"

# Remove quotes if present in ENV_MODE
ENV_MODE=$(echo "$ENV_MODE" | tr -d '"')


if [ "$ENV_MODE" = 'prod' ] ; then
    echo "Running in production mode..."
    export OPENTELEMETRY_SERVICE_NAME=django-app-gunicorn
    exec gunicorn core.wsgi:application --config=gunicorn_conf.py
elif [ "$ENV_MODE" = 'dev' ]; then
    echo "Running in development mode..."
    export OPENTELEMETRY_SERVICE_NAME=django-app-gunicorn
    exec gunicorn core.wsgi:application --config=gunicorn_conf.py
elif [[ "$ENV_MODE" == *celery_worker* ]]; then
    export OPENTELEMETRY_SERVICE_NAME=celery-worker
    exec celery -A core worker --loglevel=info
elif [[ "$ENV_MODE" == *celery_beat* ]]; then
    export OPENTELEMETRY_SERVICE_NAME=celery-beat
    exec celery -A core beat --loglevel=info
elif [ "$ENV_MODE" = 'celery_flower' ]; then
    exec celery -A core flower --loglevel=info
elif [ "$ENV_MODE" = 'local' ]; then
    echo "Running in local mode, please run migrations and server manually..."
    tail -f /dev/null
fi