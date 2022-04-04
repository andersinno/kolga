import re
from pathlib import Path
from typing import Generator, List, Optional

from kolga.utils.logger import logger
from kolga.utils.models import DockerImage, ImageStage

from ..settings import settings
from ..utils.general import get_environment_vars_by_prefix, run_os_command


class Docker:
    """
    A wrapper class around various Docker tools
    """

    STAGE_REGEX = re.compile(
        r"^FROM .*?(?: +AS +(?P<stage>.*))?$", re.IGNORECASE | re.MULTILINE
    )
    ICON = "🐳"

    def __init__(self, dockerfile: str = settings.DOCKER_BUILD_SOURCE) -> None:
        self.dockerfile = Path(dockerfile)
        self.docker_context = Path(settings.DOCKER_BUILD_CONTEXT)

        self.image_repo = f"{settings.CONTAINER_REGISTRY_REPO}"
        if settings.DOCKER_IMAGE_NAME:
            self.image_repo = f"{self.image_repo}/{settings.DOCKER_IMAGE_NAME}"
        self.image_tag = f"{self.image_repo}:{settings.GIT_COMMIT_SHA}"

        self.cache_repo = f"{self.image_repo}/{settings.BUILDKIT_CACHE_IMAGE_NAME}"
        if settings.BUILDKIT_CACHE_REPO:
            self.cache_repo = (
                f"{settings.BUILDKIT_CACHE_REPO}/{settings.BUILDKIT_CACHE_IMAGE_NAME}"
            )

        if not self.dockerfile.exists():
            raise FileNotFoundError(f"No Dockerfile found at {self.dockerfile}")

        if not self.docker_context.exists():
            raise NotADirectoryError(f"No such folder found, {self.docker_context}")

        if self.docker_context not in self.dockerfile.parents:
            raise ValueError(
                f"Dockerfile {self.dockerfile} not in build context {self.docker_context}"
            )

    def stage_image_tag(self, stage: str) -> str:
        if not stage:
            return self.image_tag
        return f"{self.image_tag}-{stage}"

    def test_image_tag(self, stage: str = settings.DOCKER_TEST_IMAGE_STAGE) -> str:
        return self.stage_image_tag(stage)

    def setup_buildkit(self, name: str = "kolgabk") -> None:
        with settings.plugin_manager.lifecycle.buildx_setup_buildkit():
            setup_command = [
                "docker",
                "buildx",
                "create",
                "--name",
                name,
                "--use",
            ]

            result = run_os_command(setup_command)
            if result.return_code:
                logger.std(result, raise_exception=True)
            else:
                logger.success(
                    icon=f"{self.ICON} 🔨",
                    message=f"New buildx builder instance is set up (Instance name: {name})",
                )

    def login(
        self,
        username: str = settings.CONTAINER_REGISTRY_USER,
        password: str = settings.CONTAINER_REGISTRY_PASSWORD,
        registry: str = settings.CONTAINER_REGISTRY,
    ) -> None:
        login_command = [
            "docker",
            "login",
            "-u",
            username,
            "-p",
            password,
            registry,
        ]

        result = run_os_command(login_command)
        if result.return_code:
            logger.std(result, raise_exception=True)
        else:
            logger.success(
                icon=f"{self.ICON} 🔑",
                message=f"Logged in to registry (User: {username})",
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

    @staticmethod
    def get_build_arguments() -> List[str]:
        """
        Get build arguments from environment

        Returns:
            List of build arguments
        """
        build_args: List[str] = []
        for key, value in get_environment_vars_by_prefix(
            settings.DOCKER_BUILD_ARG_PREFIX
        ).items():
            build_args.append(f"--build-arg={key}={value}")
        return build_args

    def get_stage_names(self) -> List[str]:
        stage_names = []

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
                stage_names.append(stage_name)
        return stage_names

    def get_stages(self) -> List[ImageStage]:
        stages: List[ImageStage] = []
        stage_names = self.get_stage_names()
        if not stage_names:
            return stages

        for stage in stage_names[:-1]:
            image_stage = ImageStage(name=stage)
            if (
                settings.DOCKER_TEST_IMAGE_STAGE
                and stage == settings.DOCKER_TEST_IMAGE_STAGE
            ):
                image_stage.development = True
                image_stage.build = True
            stages.append(image_stage)

        final_image = ImageStage(name=stage_names[-1], final=True, build=True)
        stages.append(final_image)

        return stages

    def get_image_tags(self, stage: str = "", final_image: bool = False) -> List[str]:
        def extra_tags(postfix: Optional[str] = None) -> Generator[str, None, None]:
            postfix = postfix or ""
            if settings.DOCKER_IMAGE_TAGS is None:
                yield f"{self.get_docker_git_ref_tag()}{postfix}"
            else:
                yield from (f"{tag}{postfix}" for tag in settings.DOCKER_IMAGE_TAGS)

        postfix = f"-{stage}" if stage else ""
        tags = {f"{settings.GIT_COMMIT_SHA}{postfix}", *extra_tags(postfix)}

        if postfix and final_image:
            # Add postfix-less tags
            tags |= {settings.GIT_COMMIT_SHA, *extra_tags()}

        return sorted(tags)

    def pull_image(self, image: str) -> bool:
        logger.info(icon=f"{self.ICON} ⏬", title=f"Pulling {image}:", end=" ")
        pull_command = ["docker", "pull", image]
        result = run_os_command(pull_command, shell=False)

        if result.return_code:
            logger.std(result, raise_exception=False)
        else:
            logger.success()
            return True
        return False

    def create_cache_tag(self, postfix: str = "", ref: Optional[str] = None) -> str:
        if ref:
            git_ref_tag = ref
        else:
            git_ref_tag = self.get_docker_git_ref_tag()

        stage_postfix = f"-{postfix}" if postfix else ""

        return f"{self.cache_repo}:{git_ref_tag}{stage_postfix}"

    def get_cache_tags(self) -> List[str]:
        cache_tags: List[str] = []
        target_branch = settings.GIT_TARGET_BRANCH or settings.GIT_DEFAULT_TARGET_BRANCH

        for stage in self.get_stages():
            if stage.build:
                cache_tags.append(self.create_cache_tag(postfix=stage.name))
                cache_tags.append(
                    self.create_cache_tag(postfix=stage.name, ref=target_branch)
                )

        return cache_tags

    def build_stages(self, push_images: bool = True) -> List[DockerImage]:
        """
        Build all stages of a Dockerfile and tag them
        """
        built_images = []
        stages = self.get_stages()

        with settings.plugin_manager.lifecycle.container_build():
            for stage in stages:
                if not stage.build:
                    continue

                if stage.development:
                    logger.info(
                        icon="ℹ️",
                        title=f"Found test/development stage '{stage.name}', building that as well",
                    )

                image = self.build_stage(
                    stage.name, final_image=stage.final, push_images=push_images
                )
                built_images.append(image)

        return built_images

    def build_stage(
        self,
        stage: str = "",
        final_image: bool = False,
        push_images: bool = True,
        disable_cache: bool = settings.BUILDKIT_CACHE_DISABLE,
    ) -> DockerImage:
        title = f"Building stage '{stage}': "
        if settings.DOCKER_BUILD_PLATFORMS:
            title += f" {settings.DOCKER_BUILD_PLATFORMS}"
        logger.info(icon=f"{self.ICON} 🔨", title=title)

        build_command = [
            "docker",
            "buildx",
            "build",
            f"--file={self.dockerfile.absolute()}",
            f"--target={stage}",
            "--progress=plain",
        ]

        build_command.extend(self.get_build_arguments())

        if push_images:
            build_command.append("--push")

        if not disable_cache:
            cache_to = self.create_cache_tag(postfix=stage)
            logger.info(title=f"\t ℹ️ Cache to: {cache_to}")
            build_command.append(f"--cache-to=type=registry,ref={cache_to},mode=max")

            for cache_tag in self.get_cache_tags():
                logger.info(title=f"\t ℹ️ Cache from: {cache_tag}")
                build_command.append(f"--cache-from=type=registry,ref={cache_tag}")

        if settings.DOCKER_BUILD_PLATFORMS:
            platforms = ",".join(
                platform.strip() for platform in settings.DOCKER_BUILD_PLATFORMS
            )
            build_command.append(f"--platform={platforms}")

        tags = self.get_image_tags(stage, final_image=final_image)

        for tag in tags:
            build_command.append(f"--tag={self.image_repo}:{tag}")

        build_command.append(f"{self.docker_context.absolute()}")

        image = DockerImage(repository=self.image_repo, tags=tags)

        with settings.plugin_manager.lifecycle.container_build_stage(
            image=image, stage=stage
        ):
            result = run_os_command(build_command, shell=False)
            if result.return_code:
                logger.std(result, raise_exception=True)
            else:
                for tag in tags:
                    logger.info(title=f"\t 🏷 Tagged: {self.image_repo}:{tag}")

        return image

    def delete_image(self, image: DockerImage) -> None:
        logger.warning(icon=f"{self.ICON}", message="Removing Docker image")
        for tag in image.tags:
            logger.info(message=f"\t {image.repository}:{tag}: ", end="")
            delete_command = ["docker", "rmi", f"{image.repository}:{tag}"]
            result = run_os_command(delete_command, shell=False)

            if result.return_code:
                logger.std(result, raise_exception=False)
            else:
                logger.success()
