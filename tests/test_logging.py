from typing import Any
from unittest import mock

import pytest

from kolga.settings import settings
from kolga.utils.logger import logger
from kolga.utils.models import SubprocessResult


@pytest.mark.parametrize(
    "debug, has_output",
    [
        (1, True),  # Debug on
        (0, False),  # Debug off
    ],
)
def test_debug_logging(debug: int, has_output: bool, capsys: Any) -> None:
    message = "Debug Test Message"

    with mock.patch.object(settings, "KOLGA_DEBUG", debug):
        logger.debug(message=message)
        captured = capsys.readouterr()
        if has_output:
            assert message in captured.out
        else:
            assert message not in captured.out


@pytest.mark.parametrize(
    "debug, has_output",
    [
        (1, True),  # Debug on
        (0, False),  # Debug off
    ],
)
def test_debug_std_logging(debug: int, has_output: bool, capsys: Any) -> None:
    out_message = "Output test"
    err_message = "Error test"
    return_code = 1
    command = "test"
    result = SubprocessResult(
        out=out_message,
        err=err_message,
        return_code=return_code,
        child=None,
        command=command,
    )

    with mock.patch.object(settings, "KOLGA_DEBUG", debug):
        logger.debug_std(std=result)
        captured = capsys.readouterr()
        if has_output:
            assert out_message in captured.out
            assert err_message in captured.out
            assert captured.out[2:9] == f"{command}: {return_code}"
        else:
            assert out_message not in captured.out
            assert err_message not in captured.out
            assert captured.out[2:9] != f"{command}: {return_code}"
