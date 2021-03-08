import re
from typing import Callable, Generator, List, Union

from kolga.utils.models import BasicAuthUser

BASIC_AUTH_REGEX = re.compile(r"(?P<credential>[^:\s]+:[^:\s]+)+", re.IGNORECASE)


class BasicAuthUserList(List[BasicAuthUser]):
    @classmethod
    def __get_validators__(
        cls,
    ) -> Generator[Callable[..., List[BasicAuthUser]], None, None]:
        yield cls.validate

    @classmethod
    def validate(cls, v: Union[None, str, List[BasicAuthUser]]) -> List[BasicAuthUser]:
        if v is None:
            return []
        elif not isinstance(v, str):
            return v

        credentials = BASIC_AUTH_REGEX.findall(v)
        users = []
        for credential in credentials:
            if credential:
                user = BasicAuthUser.from_colon_string(credential)
                if user:
                    users.append(user)
        return users
