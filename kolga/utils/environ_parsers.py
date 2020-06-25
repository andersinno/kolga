import re
from typing import Any, List

from kolga.utils.models import BasicAuthUser

BASIC_AUTH_REGEX = re.compile(r"(?P<credential>[^:\s]+:[^:\s]+)+", re.IGNORECASE)


def basicauth_parser(value: str) -> List[BasicAuthUser]:
    if not value:
        return []

    credentials = BASIC_AUTH_REGEX.findall(value)
    users = []
    for credential in credentials:
        if credential:
            user = BasicAuthUser.from_colon_string(credential)
            if user:
                users.append(user)
    return users


def list_none_parser(value: str) -> Any:
    """
    Identical parser to environs normal list parser, but with None support

    Args:
        value: A string value from the environment, or None

    Returns:
        A list from the string, or empty list in the case of
        empty string or None
    """
    if not value:
        return []

    return value.strip().replace(" ", "").split(",")
