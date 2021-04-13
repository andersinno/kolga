import re
from typing import Any, List, Optional, TypeVar, Union

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


def list_none_parser(
    value: Union[str, List[str], None], **kwargs: Any
) -> Optional[List[str]]:
    """
    Parse a comma-separated string into a list

    Identical to environs normal list parser, but with None and string unescaping support.

    Args:
        value: An optional string value from the environment, or the given default value

    Returns:
        A list from the string, or empty list in the case of
        empty string. Non-string values (``None``, ``[]``) are returned as-is.
    """
    if not isinstance(value, str):
        return value

    stripped_items = (item.strip() for item in value.split(","))
    return [str_unescape(item, **kwargs) for item in stripped_items if item]


_StrOrNone = TypeVar("_StrOrNone", str, None)


def str_unescape(
    value: _StrOrNone, unescape: bool = False, **kwargs: Any
) -> _StrOrNone:
    if not value:
        return value
    elif unescape:
        return unescape_string(value)
    else:
        return value
