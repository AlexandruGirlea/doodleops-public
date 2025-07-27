"""
Run this script in the CI/CD pipeline to test the connections to the MySQL and
Redis databases.
"""

import databases
import redis
import asyncio

from app_web.common.os_env_var_management import get_env_variable


ENV_MODE = get_env_variable("ENV_MODE")

# Redis Connection
REDIS_HOST = get_env_variable("REDIS_HOST")
REDIS_PORT = get_env_variable("REDIS_PORT")
REDIS_DB_DEFAULT = get_env_variable("REDIS_DB_DEFAULT")

MYSQL_DATABASE = get_env_variable("MYSQL_DATABASE")
MYSQL_USER = get_env_variable("MYSQL_USER")
MYSQL_PASSWORD = get_env_variable("MYSQL_PASSWORD")
MYSQL_HOST = get_env_variable("MYSQL_HOST")
MYSQL_PORT = get_env_variable("MYSQL_PORT")
DATABASE_URL = (
    f"mysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/"
    f"{MYSQL_DATABASE}"
)

DATABASE_URL = DATABASE_URL.replace("mysql", "mysql+pymysql")

database = databases.Database(DATABASE_URL)


async def test_mysql_connection():
    await database.connect()
    query = "SHOW TABLES;"
    results = await database.fetch_all(query=query)
    print("MySQL Tables:")
    for result in results:
        print(result[0])
    await database.disconnect()


def test_redis_connection():
    print("Redis Keys:")
    redis_conn = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB_DEFAULT,
    )
    for key in redis_conn.keys():
        print(key)


# Running both tests
async def run_tests():
    await test_mysql_connection()
    test_redis_connection()

if __name__ == "__main__":
    asyncio.run(run_tests())
