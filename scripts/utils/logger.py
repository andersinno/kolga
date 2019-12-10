from typing import Optional

import colorful as cf

from scripts.utils.models import SubprocessResult


class Logger:
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
        message_string = message if message else "An error occured"
        _message = self._create_message(message_string, icon)

        if error and not raise_exception:
            _message += f"{error}"

        print(f"{cf.red}{_message}{cf.reset}")
        if raise_exception:
            error = error or Exception(message_string)
            raise error

    def warning(self, message: str, icon: Optional[str] = None) -> None:
        _message = self._create_message(message, icon)
        print(f"{cf.yellow}{_message}{cf.reset}")

    def success(self, message: str = "", icon: Optional[str] = None) -> None:
        message_string = message if message else "Done"
        _message = self._create_message(message_string, icon)
        print(f"{cf.green}{_message}{cf.reset}")

    def info(
        self,
        message: str = "",
        title: str = "",
        icon: Optional[str] = None,
        end: str = "\n",
    ) -> None:
        message_string = (
            f"{cf.bold}{title}{cf.reset}{message}" if title else f"{message}"
        )
        _message = self._create_message(message_string, icon)
        print(f"{_message}", end=end, flush=True)

    def std(
        self,
        std: SubprocessResult,
        raise_exception: bool = False,
        log_error: bool = True,
    ) -> None:
        if log_error:
            logger.error(message=std.err, raise_exception=False)
        output_string = f"\n{cf.green}stdout:\n{cf.reset}{std.out}\n{cf.red}stderr:\n{cf.reset}{std.err}"

        if raise_exception:
            raise Exception(output_string)
        else:
            print(output_string)


logger = Logger()
