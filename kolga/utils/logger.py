from typing import Optional

import colorful as cf

from kolga.utils.models import SubprocessResult


class Logger:
    """
    Class for logging of events in the DevOps pipeline
    """

    def _create_message(self, message: str, icon: Optional[str] = None) -> str:
        icon_string = f"{icon} " if icon else ""
        return f"{icon_string}{message}"

    def error(
        self,
        message: str = "",
        icon: Optional[str] = None,
        error: Optional[Exception] = None,
        raise_exception: bool = True,
    ) -> None:
        """
        Log formatted errors to stdout and optionally raise them

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

        print(f"{cf.red}{_message}{cf.reset}")  # noqa: T001
        if raise_exception:
            error = error or Exception(message_string)
            raise error

    def warning(self, message: str, icon: Optional[str] = None) -> None:
        """
        Log formatted warnings to stdout

        Args:
            message: Verbose/Custom error message of the exception
            icon: Icon to place as before the output
        """
        _message = self._create_message(message, icon)
        print(f"{cf.yellow}{_message}{cf.reset}")  # noqa: T001

    def success(self, message: str = "", icon: Optional[str] = None) -> None:
        """
        Log formatted successful events to stdout

        Args:
            message: Verbose/Custom error message of the exception
            icon: Icon to place as before the output
        """
        message_string = message if message else "Done"
        _message = self._create_message(message_string, icon)
        print(f"{cf.green}{_message}{cf.reset}")  # noqa: T001

    def info(
        self,
        message: str = "",
        title: str = "",
        icon: Optional[str] = None,
        end: str = "\n",
    ) -> None:
        """
        Log formatted info events to stdout

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
        print(f"{_message}", end=end, flush=True)  # noqa: T001

    def std(
        self,
        std: SubprocessResult,
        raise_exception: bool = False,
        log_error: bool = True,
    ) -> None:
        """
        Log results of :class:`SubprocessResult` warnings to stdout

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
            print(output_string)  # noqa: T001


logger = Logger()
