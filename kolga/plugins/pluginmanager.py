from typing import TYPE_CHECKING

from pluggy import PluginManager

from kolga.hooks.hookspec import KolgaHookSpec, LifeCycleManager

if TYPE_CHECKING:
    PluginManagerBase = PluginManager[KolgaHookSpec]
else:
    PluginManagerBase = PluginManager


class KolgaPluginManager(PluginManagerBase):
    def __init__(self) -> None:
        super().__init__("kolga")

        self.add_hookspecs(KolgaHookSpec)
        self.lifecycle = LifeCycleManager(self)
