import git as _git

from scripts.utils.logger import logger


class Git:
    """
    A wrapper class around various Git tools
    """

    ICON = "🐙"

    def __init__(self, repo_path: str = "") -> None:
        self.repo_path = repo_path
        self.repo = _git.Repo(repo_path)

    def update_submodules(self) -> None:
        """
        Update all submodules (git submodules update --init)

        Returns:
            None
        """
        logger.info(icon=f"{self.ICON} 🌱", title="Updating submodules: ", end="")
        if not self.repo.submodules:
            logger.success("No submodules found")
        else:
            # Add new line since we ended the previous log without it
            logger.info("")
        for submodule in self.repo.submodules:
            logger.info(title=f"\t{submodule}: ", end="")
            try:
                submodule.update(init=True)
            except Exception as e:
                logger.error(error=e, raise_exception=True)
            else:
                logger.success()
