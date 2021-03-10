import re
from typing import Any, List, Optional, cast

from kolga.utils.general import unescape_string
from kolga.utils.models import BasicAuthUser

BASIC_AUTH_REGEX = re.compile(r"(?P<credential>[^:\s]+:[^:\s]+)+", re.IGNORECASE)


def basicauth_parser(value: str, **kwargs: Any) -> List[BasicAuthUser]:
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


def list_none_parser(value: str, **kwargs: Any) -> List[str]:
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

    stripped_items = (item.strip() for item in value.split(","))
    return [cast(str, str_unescape(item, **kwargs)) for item in stripped_items if item]


def str_unescape(
    value: Optional[str], unescape: bool = False, **kwargs: Any
) -> Optional[str]:
    if not value:
        return value
    elif unescape:
        return unescape_string(value)
    else:
        return value
