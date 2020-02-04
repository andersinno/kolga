import pytest

from scripts.utils.models import DockerImageRef


@pytest.mark.parametrize(  # type: ignore
    "ref, registry, repository, tag",
    (
        (
            "docker.io/bitnami/postgresql:9.6-alpine",
            "docker.io",
            "bitnami/postgresql",
            "9.6-alpine",
        ),
        ("bitnami/postgresql:9.6-alpine", None, "bitnami/postgresql", "9.6-alpine"),
        ("docker.io/bitnami/postgresql", "docker.io", "bitnami/postgresql", None),
        ("docker-io/bitnami/postgresql", None, "docker-io/bitnami/postgresql", None),
    ),
)
def test_docker_image_ref_parse(
    ref: str, registry: str, repository: str, tag: str
) -> None:
    image = DockerImageRef.parse_string(ref)

    assert image.registry == registry
    assert image.repository == repository
    assert image.tag == tag
