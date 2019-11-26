from dataclasses import dataclass, field
from typing import Any, Set

from docker.models.images import Image


@dataclass
class DockerImage:
    obj: Image
    repository: str
    local_tags: Set[str] = field(default_factory=lambda: set())
    remote_tags: Set[str] = field(default_factory=lambda: set())

    @property
    def unsynced_tags(self) -> Set[str]:
        return self.local_tags - self.remote_tags


@dataclass
class SubprocessResult:
    out: str
    err: str
    return_code: int
    child: Any
