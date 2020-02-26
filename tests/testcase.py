from functools import wraps
from typing import Any, Dict, Optional

from scripts.settings import settings


class override_settings:
    """
    Decorator for overriding settings values

    Name shamelessly stolen from Djangos own settings override
    function so that it some developers might be reminded of its
    uses.

    TODO: Support class decoration if needed
    """

    def decorate_callable(self, func: Any) -> Any:
        @wraps(func)
        def inner(*args: Any, **kwargs: Any) -> Any:
            with self:
                return func(*args, **kwargs)

        return inner

    def __call__(self, decorated: Any) -> Any:
        if callable(decorated):
            return self.decorate_callable(decorated)
        raise TypeError("Cannot decorate object of type %s" % type(decorated))

    def __init__(self, **kwargs: Any) -> None:
        self.options = kwargs
        self.old_values: Dict[str, Any] = {}
        super().__init__()

    def __enter__(self) -> None:
        return self.enable()

    def __exit__(
        self,
        exc_type: Optional[Any],
        exc_value: Optional[Any],
        traceback: Optional[Any],
    ) -> None:
        self.disable()

    def enable(self) -> None:
        for key, new_value in self.options.items():
            if not hasattr(settings, key):
                continue
            self.old_values[key] = getattr(settings, key, None)
            setattr(settings, key, new_value)

    def disable(self) -> None:
        for key, old_value in self.old_values.items():
            setattr(settings, key, old_value)
