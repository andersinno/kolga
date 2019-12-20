import re
from typing import List

from scripts.utils.models import BasicAuthUser

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
