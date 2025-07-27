import json
import logging
from typing import Union

import redis

from django.conf import settings


logger = logging.getLogger(__name__)


class RedisClient:
    def __init__(self):
        self._instance = None

    def __enter__(self):
        if self._instance is None:
            self._instance = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB_DEFAULT,
            )
        return self._instance

    def __exit__(self, exc_type, exc_value, traceback):
        if self._instance is not None:
            self._instance.connection_pool.disconnect()
            self._instance = None

    def type(self, key):
        if self._instance is not None:
            return self._instance.type(key)
        return None


def delete_all_keys():
    if settings.ENV_MODE == "prod":
        logger.error(
            "This `delete_all_keys` function should not be called in prod."
        )
        return
    print("Flushing Redis DB...pt1")
    with RedisClient() as client:
        if client is not None:
            client.flushdb()
        else:
            raise Exception("Not connected to Redis.")


def set_redis_key(
    key: str,
    simple_value: Union[str, int, float] = None,
    expire: int = None,
    timed_value: dict = None,
    timestamp: Union[int, float] = None,
) -> bool:
    """
    Set redis key
        :param key: name
        :param simple_value: simple value
        :param expire: number of seconds until the key expires. Not a timestamp!
        :param timed_value: is a dictionary that will be stored as a JSON string
        :param timestamp: is used as the score for the timed value to sort by
        :return: True if success or Raise ValueError
    """
    with RedisClient() as client:
        if simple_value or simple_value == 0:
            if expire:
                client.setex(key, expire, simple_value)
            else:
                client.set(key, simple_value)

        elif timed_value and timestamp:
            timed_value_str = json.dumps(timed_value)
            client.zadd(key, {timed_value_str: timestamp})

            # If expire is provided, set an expiration for the sorted set.
            if expire:
                client.expire(key, expire)
        else:
            raise ValueError(
                "Either value or both timed_value and timestamp must be provided."
            )
    return True


def get_redis_key(
    key: str,
    min_timestamp: Union[int, float, str] = "-inf",
    max_timestamp: Union[int, float, str] = "+inf",
) -> Union[str, list] or None:
    """
    Get redis key value or sorted set based on different parameters
        :param key: the redis key
        :param min_timestamp: minimum score for ZRANGEBYSCORE
        :param max_timestamp: maximum score for ZRANGEBYSCORE
        :return: value or list of values
    """
    try:
        with RedisClient() as client:
            redis_key_type = client.type(key).decode("utf-8")

            if redis_key_type == "none":
                logger.warning(f"The key {key} does not exist.")
                return None

            elif (
                redis_key_type == "string"
                and min_timestamp == "-inf"
                and max_timestamp == "+inf"
            ):
                return client.get(key).decode("utf-8")

            elif redis_key_type == "zset":
                return [
                    json.loads(x.decode("utf-8"))
                    for x in client.zrangebyscore(
                        key, min_timestamp, max_timestamp
                    )
                ]
            logger.error(
                f"The key {key} holds a type {redis_key_type}, can't be handled."
            )

    except Exception as e:
        logger.error(e)


def get_redis_keys_by_pattern(pattern: str) -> list:
    """
    Get redis keys by pattern
        :param pattern: the pattern to match
        :return: list of keys
    """
    with RedisClient() as client:
        return client.keys(pattern)


def delete_redis_key(key: str) -> bool:
    """
    Delete redis key
        :param key: the redis key
        :return: True or False
    """
    with RedisClient() as client:
        return client.delete(key)


def rename_redis_key(template_key: str, old_value:str, new_value: str) -> None:
    """
    Renames all Redis keys containing
    Ex: key_pattern = "credits_used_per_api_endpoint_by_user:*:{old_value}:*:*:*"

    Args:
        old_username (str): The username to be replaced.
        new_username (str): The new username to replace with.
    """
    expected_parts = template_key.split(":")

    if ":{old_value}:*" not in template_key:
        raise ValueError(
            "The key pattern must contain the old value to be replaced."
        )
    key_pattern = template_key.format(old_value=old_value)
    logger.info(f"Starting to rename keys matching pattern: {key_pattern}")

    with RedisClient() as redis_client:
        cursor = 0
        while True:
            cursor, keys = redis_client.scan(cursor=cursor, match=key_pattern,
                                             count=1000)
            logger.info(f"Scan returned {len(keys)} keys")

            for key in keys:
                key = key.decode("utf-8")
                if len(key.split(':')) != len(expected_parts):
                    logger.warning(f"Key format unexpected, skipping key: {key}")
                    continue  # Skip keys that don't match the expected format

                # Replace the username part
                new_key = key.replace(old_value, new_value)

                try:
                    # Check if the new key already exists to avoid overwriting
                    if redis_client.exists(new_key):
                        logger.warning(
                            f"New key already exists, skipping rename: {new_key}")
                        continue

                    # Rename the key
                    redis_client.rename(key, new_key)
                    logger.info(f"Renamed key from {key} to {new_key}")

                except redis.RedisError as e:
                    logger.error(f"Error renaming key {key} to {new_key}: {e}")

            if cursor == 0:
                break  # No more keys to scan

    logger.info("Completed renaming keys.")
