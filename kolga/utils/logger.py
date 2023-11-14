import sys
import time
from contextlib import contextmanager
from functools import partial
from typing import Callable, Generator, Optional

import colorful as cf

from kolga.utils.models import SubprocessResult


class Logger:
    """
    Class for logging of events in the DevOps pipeline
    """

    def _create_message(self, message: str, icon: Optional[str] = None) -> str:
        icon_string = f"{icon} " if icon else ""
        return f"{icon_string}{message}"

    def __create_section_data(self, section_name: str, collapsed: bool) -> str:
        collapsed_string = "true" if collapsed else "false"
        now = int(time.time())
        section_info = f"{section_name}[collapsed={collapsed_string}]\r\033[0K"
        return f"{now}:{section_info}"

    def start_section(
        self, section_title: str, section_name: str, collapsed: bool = False
    ) -> Callable[[], None]:
        section_data = self.__create_section_data(section_name, collapsed)
        section_message = f"section_start:{section_data}{section_title}"

        print(section_message, file=sys.stderr)  # noqa: T201

        return partial(self.end_section, section_name=section_name, collapsed=collapsed)

    def end_section(self, section_name: str, collapsed: bool = False) -> None:
        section_data = self.__create_section_data(section_name, collapsed)
        section_message = f"section_end:{section_data}"

        print(section_message, file=sys.stderr)  # noqa: T201

    @contextmanager
    def do_section(
        self, section_title: str, section_name: str, collapsed: bool = False
    ) -> Generator[None, None, None]:
        end_section = self.start_section(section_title, section_name, collapsed)
        try:
            yield
        except Exception as e:
            end_section()
            raise e
        finally:
            end_section()

    def debug(
        self,
        message: str = "",
        icon: Optional[str] = "🐛",
    ) -> None:
        """
        Log formatted warnings to stderr

        Args:
            message: Debug message
            icon: Icon to place as before the output
        """
        from kolga.settings import settings

        if settings.KOLGA_DEBUG:
            _message = self._create_message(message, icon)
            print(f"{cf.purple}{_message}{cf.reset}", file=sys.stderr)  # noqa: T201

    def debug_std(
        self,
        result: SubprocessResult,
    ) -> None:
        return_code_color = cf.green if result.return_code == 0 else cf.red
        self.debug(
            message=f"{result.command}: {return_code_color}{result.return_code}{cf.reset}"
        )

        if result.out:
            self.debug(message=f"{result.out}")

        if result.err:
            self.debug(message=f"{result.err}")

    def error(
        self,
        message: str = "",
        icon: Optional[str] = None,
        error: Optional[Exception] = None,
        raise_exception: bool = True,
    ) -> None:
        """
        Log formatted errors to stderr and optionally raise them

        Args:
            message: Verbose/Custom error message of the exception
            icon: Icon to place as before the output
            error: Exception should be logged and optionally raised
            raise_exception: If True, raise `error` if passed, otherwise raise `Exception`
        """
        message_string = message if message else "An error occured"
        _message = self._create_message(message_string, icon)

        if error and not raise_exception:
            _message += f"{error}"

        print(f"{cf.red}{_message}{cf.reset}", file=sys.stderr)  # noqa: T201
        if raise_exception:
            error = error or Exception(message_string)
            raise error

    def warning(self, message: str, icon: Optional[str] = None) -> None:
        """
        Log formatted warnings to stderr

        Args:
            message: Verbose/Custom error message of the exception
            icon: Icon to place as before the output
        """
        _message = self._create_message(message, icon)
        print(f"{cf.yellow}{_message}{cf.reset}", file=sys.stderr)  # noqa: T201

    def success(self, message: str = "", icon: Optional[str] = None) -> None:
        """
        Log formatted successful events to stderr

        Args:
            message: Verbose/Custom error message of the exception
            icon: Icon to place as before the output
        """
        message_string = message if message else "Done"
        _message = self._create_message(message_string, icon)
        print(f"{cf.green}{_message}{cf.reset}", file=sys.stderr)  # noqa: T201

    def info(
        self,
        message: str = "",
        title: str = "",
        icon: Optional[str] = None,
        end: str = "\n",
    ) -> None:
        """
        Log formatted info events to stderr

        Args:
            title: Title of the message, printed in bold
            message: Verbose/Custom error message of the exception
            icon: Icon to place as before the output
            end: Ending char of the message, for controlling new line for instance
        """
        message_string = (
            f"{cf.bold}{title}{cf.reset}{message}" if title else f"{message}"
        )
        _message = self._create_message(message_string, icon)
        print(f"{_message}", end=end, file=sys.stderr, flush=True)  # noqa: T201

    def std(
        self,
        std: SubprocessResult,
        raise_exception: bool = False,
        log_error: bool = True,
    ) -> None:
        """
        Log results of :class:`SubprocessResult` warnings to stderr

        Args:
            std: Result from a subprocess call
            raise_exception: If True, raise `Exception`
            log_error: If True, log the error part of the result with :func:`~Logger.error`
        """
        if log_error:
            logger.error(message=std.err, raise_exception=False)
        output_string = f"\n{cf.green}stdout:\n{cf.reset}{std.out}\n{cf.red}stderr:\n{cf.reset}{std.err}"

        if raise_exception:
            raise Exception(output_string)
        else:
            print(output_string, file=sys.stderr)  # noqa: T201


logger = Logger()
