from typing import Tuple, Type

from kolga.hooks.plugins import PluginBase
from kolga.plugins.sentry.sentry import KolgaSentryPlugin
from kolga.plugins.slack.slack import KolgaSlackPlugin

KOLGA_CORE_PLUGINS: Tuple[Type[PluginBase], ...] = (
    KolgaSentryPlugin,
    KolgaSlackPlugin,
)
