from dataclasses import dataclass, field
from typing import Any, Optional, Set

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
class DockerImageRef:
    registry: Optional[str]
    repository: str
    tag: Optional[str]

    @classmethod
    def parse_string(cls, ref: str) -> "DockerImageRef":
        registry: Optional[str] = None
        repository: Optional[str] = None
        tag: Optional[str] = None

        if "." in ref:
            registry, rest = ref.split("/", 1)
        else:
            rest = ref

        if ":" in rest:
            repository, tag = rest.split(":", 1)
        else:
            repository = rest

        return cls(registry=registry, repository=repository, tag=tag)


@dataclass
class SubprocessResult:
    out: str
    err: str
    return_code: int
    child: Any


@dataclass
class ReleaseStatus:
    pods: str = ""
    deployment: str = ""

    def __str__(self) -> str:
        result = "==== POD STATUSES ====\n"
        result += self.pods
        result += "==== DEPLOYMENT STATUS ====\n"
        result += self.deployment
        return result


@dataclass
class BasicAuthUser:
    username: str
    password: str

    @classmethod
    def from_colon_string(cls, colon_string: str) -> "BasicAuthUser":
        username, password = colon_string.split(":")
        return cls(username=username, password=password)
