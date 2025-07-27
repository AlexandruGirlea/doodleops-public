#!/bin/bash
# stopping the execution at the first sign of trouble
set -e

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

if [ "$ENV_MODE" = 'prod' ] ; then
    echo "Running in production mode..."
    python uvicorn_config.py
elif [ "$ENV_MODE" = 'dev' ]; then
    echo "Running in development mode..."
    python uvicorn_config.py
elif [ "$ENV_MODE" = 'local' ]; then
    echo "Running in local mode, please run server manually..."
    tail -f /dev/null
else
    echo "Error: ENV_MODE is not set to a valid value. Exiting..." >&2
fi