#!/bin/bash
# stopping the execution at the first sign of trouble
set -e

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