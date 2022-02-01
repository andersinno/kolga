from importlib import import_module
from pathlib import Path
from typing import Callable, Generator, Iterator, Optional, Type, TypeVar

from kolga.plugins.base import PluginBase
from kolga.utils.logger import logger


def _import_plugins(
    directory: Optional[Path] = None,
) -> Generator[Type[PluginBase], None, None]:
    if not directory:
        directory = Path(__file__).parent

    for init_file in directory.glob("*/__init__.py"):
        module_name = init_file.parent.name
        module = import_module(f".{module_name}", package=__package__)

        try:
            yield getattr(module, "Plugin")
        except AttributeError:
            logger.warning(f"Unable to load plugin: {module_name}")


_T = TypeVar("_T")


_T_Populate = Callable[[], Generator[_T, None, None]]


class _LazyList(list[_T]):
    def __init__(self, populate: _T_Populate[_T]) -> None:
        self._populate: Optional[_T_Populate[_T]] = populate

    def __iter__(self) -> Iterator[_T]:
        if self._populate is not None:
            self.extend(self._populate())
            self._populate = None

        return super().__iter__()


KOLGA_CORE_PLUGINS = _LazyList(_import_plugins)
