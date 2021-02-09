from typing import Any, List

from kolga.plugins.sentry.sentry import KolgaSentryPlugin
from kolga.plugins.slack.slack import KolgaSlackPlugin

KOLGA_CORE_PLUGINS: List[Any] = [
    KolgaSentryPlugin,
    KolgaSlackPlugin,
]
