import re
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Generator,
    List,
    Optional,
    Type,
    Union,
)

from kolga.utils.models import BasicAuthUser

if TYPE_CHECKING:
    from pydantic import BaseConfig
    from pydantic.dataclasses import Dataclass
    from pydantic.fields import ModelField
    from pydantic.main import BaseModel


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


def split_comma_separated_values(
    settings: Union[Type["BaseModel"], Type["Dataclass"], None],
    value: Optional[Union[str, List[str]]],
    values: Dict[str, Any],
    field: "ModelField",
    config: Type["BaseConfig"],
) -> Optional[List[str]]:
    if isinstance(value, str):
        # Split at comma, strip whitespace, and filter out falsy values.
        value = [*filter(None, map(str.strip, value.split(",")))]
    return value
