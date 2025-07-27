"""
This was needed because of the way Env Variables where being passed to the docker
container that is running inside the Celery VMs.
"""


import os


def get_env_variable(name, default: str | None = None) -> str | None:
    value = os.getenv(name)
    if not value:
        return default
    if value and (value.startswith('"') and value.endswith('"')):
        return value[1:-1]
    return value
