import re
from uuid import uuid4

from kolga.utils.general import DATABASE_DEFAULT_PORT_MAPPING, MYSQL
from kolga.utils.url import URL  # type: ignore


class Database:
    def __init__(self, url: URL) -> None:
        self.url = url

    @staticmethod
    def get_random_auth_database_url(
        database_driver: str, database_name: str, database_hostname: str
    ) -> URL:
        if database_driver not in DATABASE_DEFAULT_PORT_MAPPING.keys():
            raise ValueError("Database not supported")

        # Strip any non-valid chars
        database_name = re.sub(r"[^a-zA-Z0-9_]+", "_", database_name)

        username = str(uuid4()).replace("-", "")
        password = str(uuid4()).replace("-", "")
        return URL(
            drivername=database_driver,
            database=database_name,
            username=username,
            password=password,
            host=database_hostname,
            port=DATABASE_DEFAULT_PORT_MAPPING[database_driver],
        )

    @staticmethod
    def get_database_creation_sql_from_url(url: URL) -> str:
        if url.drivername != MYSQL:
            raise ValueError("Only MySQL is supported at this time")

        sql = ""
        if url.drivername == MYSQL:
            sql = f"""
            CREATE DATABASE `{url.database}` CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
            CREATE USER IF NOT EXISTS '{url.username}'@'%' IDENTIFIED BY '{url.password}';
            GRANT ALL PRIVILEGES ON `{url.database}`.* TO '{url.username}'@'%';
            FLUSH PRIVILEGES;
            """
        return sql

    @property
    def creation_sql(self) -> str:
        return self.get_database_creation_sql_from_url(self.url)
