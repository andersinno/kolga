from typing import List

import pytest

from kolga.utils.environ_parsers import basicauth_parser
from kolga.utils.models import BasicAuthUser


@pytest.mark.parametrize(  # type: ignore
    "input, expected",
    [
        ("test:test", [BasicAuthUser(username="test", password="test")]),
        (
            "test:test, testing:testing",
            [
                BasicAuthUser(username="test", password="test,"),
                BasicAuthUser(username="testing", password="testing"),
            ],
        ),
        (
            "test:test testing::testing",
            [BasicAuthUser(username="test", password="test")],
        ),
        ("test:test testing", [BasicAuthUser(username="test", password="test")]),
        (
            "aja899€#:()Jtr4ng83",
            [BasicAuthUser(username="aja899€#", password="()Jtr4ng83")],
        ),
    ],
)
def test_non_empty_basicauth_parser(input: str, expected: List[BasicAuthUser]) -> None:
    users = basicauth_parser(input)
    for i, user in enumerate(users):
        assert user.username == expected[i].username
        assert user.password == expected[i].password


def test_empty_basicauth_parser(input: str = "test test") -> None:
    assert basicauth_parser(input) == []
