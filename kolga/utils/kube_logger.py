from pathlib import Path
from subprocess import DEVNULL, Popen, TimeoutExpired
from tempfile import NamedTemporaryFile
from threading import Event, Thread
from typing import IO, Dict, Optional, Tuple


class KubeLoggerThread(Thread):
    _cmd: Tuple[str, ...]
    _log: IO[bytes]
    _stop_event: Event
    log_path: Path
    keep_logs: bool

    TIMEOUT = 5

    def __init__(
        self,
        namespace: str,
        labels: Optional[Dict[str, str]] = None,
        keep_logs: bool = False,
    ):
        super().__init__()

        self._cmd = (
            "kubectl",
            "logs",
            "--all-containers=true",
            "--follow=true",
            "--ignore-errors=true",
            f"--namespace={namespace}",
            "--prefix",
            "--timestamps=true",
            "--selector",
            ",".join(f"{k}={v}" for k, v in (labels if labels else {}).items()),
        )
        self._log = NamedTemporaryFile(delete=False, mode="wb")
        self._stop_event = Event()
        self.keep_logs = keep_logs
        self.log_path = Path(self._log.name)

    def __del__(self) -> None:
        if not self.keep_logs:
            # Don't leave garbage lying around.
            self.log_path.unlink()

    def run(self) -> None:
        running = True
        subprocess = None

        while running:
            if subprocess:
                try:
                    # TODO: Check return value
                    _ = subprocess.wait(0)
                except TimeoutExpired:
                    # Still running. Good.
                    pass
                else:
                    # Child dead.
                    subprocess = None

            if subprocess is None:
                # (Re-)start the subprocess
                subprocess = Popen(  # nosec
                    self._cmd, shell=False, stderr=DEVNULL, stdout=self._log
                )

            # Wait on stop event
            running = not self._stop_event.wait(self.TIMEOUT)

        if subprocess:
            subprocess.kill()
            subprocess.wait()

    def stop(self) -> None:
        # Signal the poller thread
        self._stop_event.set()

        # Wait for the thread
        self.join()

        # Close the log fd
        self._log.close()
