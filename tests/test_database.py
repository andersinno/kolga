import pytest

from kolga.libs.database import Database
from kolga.utils.general import DATABASE_DEFAULT_PORT_MAPPING, MYSQL, POSTGRES
from kolga.utils.url import URL  # type: ignore


@pytest.mark.parametrize(
    "driver, database, hostname",
    [(MYSQL, "test", "localhost"), (POSTGRES, "test", "localhost")],
)
def test_get_random_auth_database_url(
    driver: str, database: str, hostname: str
) -> None:
    url = Database.get_random_auth_database_url(
        database_driver=driver, database_name=database, database_hostname=hostname
    )

    assert url.drivername == driver
    assert url.database == database
    assert url.host == hostname

    # UUID without the hyphens has a length of 32
    assert len(url.username) == 32
    assert len(url.password) == 32

    assert url.port == DATABASE_DEFAULT_PORT_MAPPING[driver]


def test_test_get_random_auth_database_url_value_error() -> None:
    with pytest.raises(ValueError):
        Database.get_random_auth_database_url(
            database_driver="monsterdb",
            database_name="test",
            database_hostname="localhost",
        )


def test_get_database_creation_sql_from_url() -> None:
    url_args = {
        "drivername": MYSQL,
        "host": "localhost",
        "username": "testuser",
        "password": "testpassword",
        "database": "testdb",
    }

    def line_checker(data: str, expected_data: str) -> None:
        split_data = data.strip().split("\n")
        split_expected_data = expected_data.strip().split("\n")

        for i, line in enumerate(split_data):
            assert line.strip() == split_expected_data[i].strip()

    url = URL(
        drivername=url_args["drivername"],
        host=url_args["host"],
        username=url_args["username"],
        password=url_args["password"],
        database=url_args["database"],
    )
    creation_query = Database.get_database_creation_sql_from_url(url)

    expected_query = f"""
        CREATE DATABASE `{url_args["database"]}` CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
        CREATE USER IF NOT EXISTS '{url_args["username"]}'@'%' IDENTIFIED BY '{url_args["password"]}';
        GRANT ALL PRIVILEGES ON `{url_args["database"]}`.* TO '{url_args["username"]}'@'%';
        FLUSH PRIVILEGES;
        """

    database = Database(url=url)

    line_checker(creation_query, expected_query)
    line_checker(database.creation_sql, expected_query)


def test_get_database_creation_sql_from_url_value_error() -> None:
    url = URL(
        drivername="monsterdb",
        host="localhost",
        username="test",
        password="test",
        database="test",
    )
    with pytest.raises(ValueError):
        Database.get_database_creation_sql_from_url(url)


def test_get_database_creation_sql_from_url_postgres() -> None:
    url = URL(
        drivername=POSTGRES,
        host="localhost",
        username="test",
        password="test",
        database="test",
    )
    with pytest.raises(ValueError):
        Database.get_database_creation_sql_from_url(url)
