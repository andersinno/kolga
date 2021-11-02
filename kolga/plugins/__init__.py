from importlib import import_module
from pathlib import Path
from typing import Generator, Optional, Tuple, Type

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


KOLGA_CORE_PLUGINS: Tuple[Type[PluginBase], ...] = tuple(_import_plugins())
