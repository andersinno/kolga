import re
from pathlib import Path
from typing import List, Optional, Set

import docker.errors

from scripts.utils.logger import logger
from scripts.utils.models import DockerImage

from ..settings import settings


class Docker:
    """
    A wrapper class around various Docker tools
    """

    STAGE_REGEX = re.compile(
        r"^FROM .*?(?: +AS +(?P<stage>.*))?$", re.IGNORECASE | re.MULTILINE
    )
    ICON = "🐳"

    def __init__(self, dockerfile: str = settings.DOCKER_BUILD_SOURCE) -> None:
        self.client = docker.DockerClient(base_url=settings.DOCKER_HOST)
        self.dockerfile = Path(dockerfile)

        self.image_repo = f"{settings.CONTAINER_REGISTRY_REPO}"
        if settings.DOCKER_IMAGE_NAME:
            self.image_repo = f"{self.image_repo}/{settings.DOCKER_IMAGE_NAME}"
        self.image_tag = f"{self.image_repo}:{settings.GIT_COMMIT_SHA}"

        self.image_cache: Set[str] = set()

        if not self.dockerfile.exists():
            raise FileExistsError(f"No Dockerfile found at {self.dockerfile}")

    def stage_image_tag(self, stage: str) -> str:
        return f"{self.image_tag}-{stage}"

    def test_image_tag(self, stage: str = settings.DOCKER_TEST_IMAGE_STAGE) -> str:
        return self.stage_image_tag(stage)

    def login(
        self,
        username: str = settings.CONTAINER_REGISTRY_USER,
        password: str = settings.CONTAINER_REGISTRY_PASSWORD,
        registry: str = settings.CONTAINER_REGISTRY,
    ) -> None:
        try:
            self.client.login(
                username=username, password=password, registry=registry, reauth=True
            )
            logger.success(
                icon=f"{self.ICON} 🔑",
                message=f"Logged in to registry (User: {username})",
            )
        except docker.errors.APIError as e:
            logger.error(
                icon=f"{self.ICON} 🔑",
                message="Docker registry login failed!",
                error=e,
                raise_exception=True,
            )

    @staticmethod
    def get_docker_git_ref_tag(
        git_commit_ref: str = settings.GIT_COMMIT_REF_NAME,
    ) -> str:
        """
        Creates a tag from the git reference that can be used as a Docker tag

        Docker does not support all characters in its tag names, for instance
        / would be seen as a separator which would break the docker tag command.
        :return:
        """
        return git_commit_ref.translate(str.maketrans("_/", "--"))

    def get_stages(self, announce: bool = True) -> List[str]:
        stages = []
        with open(self.dockerfile) as f:
            while True:
                line = f.readline()
                if not line:
                    break
                matched_stage = self.STAGE_REGEX.match(line)
                if not matched_stage:
                    continue
                stage_name = (
                    matched_stage.group("stage") if matched_stage.group("stage") else ""
                )
                stages.append(stage_name)
        if announce:
            logger.info(
                icon=f"{self.ICON} ℹ️ ",
                title=f"For {settings.DOCKER_BUILD_CONTEXT}/{self.dockerfile}, found stages: ",
                message=f"{stages}",
            )
        return stages

    def get_image_tags(self, stage: str = "", final_image: bool = False) -> List[str]:
        # Add - prefix to tag name if prefix is present
        stage_tag = f"-{stage}" if stage else stage
        git_ref_tag = self.get_docker_git_ref_tag()
        tags = {f"{settings.GIT_COMMIT_SHA}{stage_tag}", f"{git_ref_tag}{stage_tag}"}
        if final_image:
            tags |= {f"{settings.GIT_COMMIT_SHA}", f"{git_ref_tag}"}
        return sorted(tags)

    def pull_image(
        self, image: str, error_on_not_found: bool = False, raise_exception: bool = True
    ) -> bool:
        try:
            logger.info(icon=f"{self.ICON} ⏬", title=f"Pulling {image}:", end=" ")
            self.client.images.pull(image)
        except docker.errors.NotFound as e:
            logger.warning("Not found")
            if error_on_not_found:
                raise e
        except Exception:
            logger.error(raise_exception=raise_exception)
        else:
            logger.success()
            return True
        return False

    def pull_cache(
        self, suffix: Optional[str] = None, pull_commit_ref: bool = True
    ) -> Set[str]:
        pulled_images = set()
        suffix = f"-{suffix}" if suffix else ""
        master_image = f"{self.image_repo}:master{suffix}"
        if self.pull_image(master_image):
            pulled_images.add(master_image)

        if pull_commit_ref:
            # Translate _ and / to _ since those chars are not supported by docker images
            git_ref_tag = self.get_docker_git_ref_tag()
            commit_ref_image = f"{self.image_repo}:{git_ref_tag}{suffix}"
            if self.pull_image(commit_ref_image):
                pulled_images.add(commit_ref_image)

        self.image_cache |= pulled_images
        return pulled_images

    def build_stages(self) -> List[DockerImage]:
        """
        Build all stages of a Dockerfile and tag them

        We build the images in reverse order to save time in
        the case of an issues with the final build as well as
        to create a complete caching structure for subsequent
        builds.
        """
        self.pull_cache()
        built_images = []
        stages = self.get_stages()

        reverse_stages = reversed(stages)

        for i, stage in enumerate(reverse_stages):
            if i > 0:
                built_images.append(self.build_stage(stage))
            else:
                built_images.append(self.build_stage(stage, final_image=True))

        return built_images

    def build_stage(
        self,
        stage: str = "",
        path: str = settings.DOCKER_BUILD_CONTEXT,
        final_image: bool = False,
    ) -> DockerImage:
        logger.info(icon=f"{self.ICON} 🔨", title=f"Building stage '{stage}': ", end="")
        try:
            image_obj, build_log = self.client.images.build(
                path=path,
                dockerfile=settings.DOCKER_BUILD_SOURCE,
                cache_from=list(self.image_cache),
                target=stage,
            )
            image = DockerImage(image_obj, self.image_repo)
        except docker.errors.BuildError as e:
            logger.error("Build failed!", error=e, raise_exception=True)
        except Exception as e:
            logger.error(error=e, raise_exception=True)
        else:
            logger.success()

        image = self.tag_image(image, stage, final_image=final_image)

        return image

    def tag_image(
        self, image: DockerImage, stage: str = "", final_image: bool = False
    ) -> DockerImage:
        tags = self.get_image_tags(stage, final_image=final_image)

        logger.info(icon=f"{self.ICON} 🏷️ ", title="Tagging image:")
        for tag in tags:
            try:
                logger.info(title=f"\t {tag}: ", end="")
                image.obj.tag(self.image_repo, tag)
            except docker.errors.APIError as e:
                logger.error(error=e, raise_exception=True)
            else:
                logger.success()
                created_tag = f"{self.image_repo}:{tag}"
                image.local_tags.add(tag)
                self.image_cache.add(created_tag)
        return image

    def push_image(self, image: DockerImage) -> None:
        logger.info(icon=f"{self.ICON} ⏫ ", title="Pushing image(s):")
        for tag in image.unsynced_tags:
            logger.info(title=f"\t {image.repository}:{tag}: ", end="")
            try:
                self.client.images.push(
                    repository=image.repository, tag=tag, stream=False, decode=True
                )

                image.remote_tags.add(tag)
            except docker.errors.APIError as e:
                logger.error(error=e, raise_exception=True)
            logger.success()

    def push_images(self, images: List[DockerImage]) -> None:
        for image in images:
            self.push_image(image)

    def delete_image(self, image: DockerImage) -> None:
        logger.warning(icon=f"{self.ICON}", message="Removing Docker image")
        for tag in image.local_tags:
            print(f"\t {image.repository}:{tag}: ", end="", flush=True)
            try:
                self.client.images.remove(f"{image.repository}:{tag}")
            except docker.errors.ImageNotFound:
                logger.warning("Not found")
            except Exception as e:
                logger.error(error=e, raise_exception=True)
            else:
                logger.success()
