from typing import Any, Callable, TypeVar, cast

import pluggy  # type: ignore

F = TypeVar("F", bound=Callable[..., Any])
hookspec = cast(Callable[[F], F], pluggy.HookspecMarker("kolga"))


class KolgaHookSpec:
    """
    Kolga Hook Specification
    """
