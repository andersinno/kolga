from typing import List

import pytest

from kolga.utils.fields import BasicAuthUserList
from kolga.utils.models import BasicAuthUser


@pytest.mark.parametrize(
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
        (
            "username:firstpart:only",
            [BasicAuthUser(username="username", password="firstpart")],
        ),
    ],
)
def test_non_empty_basicauth_parser(input: str, expected: List[BasicAuthUser]) -> None:
    users = BasicAuthUserList.validate(input)
    for i, user in enumerate(users):
        assert user.username == expected[i].username
        assert user.password == expected[i].password


def test_empty_basicauth_parser(input: str = "test test") -> None:
    assert BasicAuthUserList.validate(input) == []
