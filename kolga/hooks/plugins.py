import os
from typing import List, Tuple

from environs import Env, ParserMethod

from .exceptions import PluginMissingConfiguration


class EmptyVariables:
    pass


class PluginBase:
    name: str
    verbose_name: str

    required_variables: List[Tuple[str, ParserMethod]] = []
    optional_variables: List[Tuple[str, ParserMethod]] = []
    configured: bool = False

    def configure(self, env: Env) -> None:
        missing_required_variables = [
            variable
            for variable, cast_func in self.required_variables
            if isinstance(env(variable, EmptyVariables()), EmptyVariables)
        ]
        if missing_required_variables:
            raise PluginMissingConfiguration(
                f"Required variables not set: {missing_required_variables}"
            )

        variables = self.required_variables + self.optional_variables
        for variable, cast_func in variables:
            if os.getenv(variable):
                setattr(self, variable, cast_func(variable))
        self.configured = True
