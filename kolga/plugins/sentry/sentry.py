import sentry_sdk
from environs import Env

from kolga.plugins.base import PluginBase


class KolgaSentryPlugin(PluginBase):
    name = "sentry"
    verbose_name = "Kolga Sentry Plugin"
    version = 0.1

    # Environment variables
    SENTRY_DSN: str
    DISABLE_SENTRY: bool

    def __init__(self, env: Env) -> None:
        self.required_variables = [("SENTRY_DSN", env.str)]
        self.optional_variables = [("DISABLE_SENTRY", env.bool)]
        self.DISABLE_SENTRY = False

        self.configure(env)

        self._setup_client()

    def _setup_client(self) -> None:
        if not self.DISABLE_SENTRY:
            sentry_sdk.init(dsn=self.SENTRY_DSN)
