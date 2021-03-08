import re
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Generator,
    Iterable,
    List,
    Optional,
    Protocol,
    Type,
    TypeVar,
    Union,
)

from kolga.utils.general import unescape_string
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


T_co = TypeVar("T_co", covariant=True)


class ConstructableIterable(Iterable[T_co], Protocol[T_co]):
    def __init__(self, __items: Iterable[T_co]) -> None:
        ...


T_OptionalStringOrIterableOfStrings = TypeVar(
    "T_OptionalStringOrIterableOfStrings", None, str, ConstructableIterable[str]
)


def unescape_string_values(
    settings: Union[Type["BaseModel"], Type["Dataclass"], None],
    value: T_OptionalStringOrIterableOfStrings,
    values: Dict[str, Any],
    field: "ModelField",
    config: Type["BaseConfig"],
) -> T_OptionalStringOrIterableOfStrings:
    if value is not None and getattr(config, "unescape_strings", False):
        if isinstance(value, str):
            value = unescape_string(value)
        else:
            value = type(value)(unescape_string(v) for v in value)
    return value
