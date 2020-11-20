from typing import Dict

import hvac  # type: ignore

from kolga.utils.logger import logger

from ..settings import settings


class Vault:
    """
    A wrapper class for Hashicorp Vault
    """

    ICON = "🗄️"

    def __init__(
        self,
        track: str,
        vault_addr: str = settings.VAULT_ADDR,
        skip_tls: bool = settings.VAULT_TLS_ENABLED,
    ) -> None:
        self.client = hvac.Client(url=vault_addr, verify=settings.VAULT_TLS_ENABLED)
        self.vault_addr = vault_addr
        self.skip_tls = skip_tls
        self.track = track
        self.initialized = False

        if self.vault_addr:
            self.initialized = True
        else:
            logger.info(
                icon=f"{self.ICON} ℹ️",
                message="VAULT_ADDR not defined. Skipping Vault usage.",
            )

    def login(self, ci_jwt: str = settings.VAULT_JWT) -> None:
        if self.initialized:
            try:
                response = self.client.auth.jwt.jwt_login(
                    role=f"{settings.PROJECT_NAME}-{self.track}",
                    jwt=ci_jwt,
                    path=settings.VAULT_JWT_AUTH_PATH,
                )
                self.client.token = response["auth"]["client_token"]
            except hvac.exceptions.Unauthorized as e:
                logger.error(
                    icon=f"{self.ICON} 🔑",
                    message="Vault login failed!",
                    error=e,
                    raise_exception=True,
                )

    def get_secrets(self) -> Dict[str, str]:
        if self.initialized:
            secrets_list = {}
            try:
                logger.info(
                    icon=f"{self.ICON} 🔑",
                    message=f"Checking for secrets in {settings.VAULT_KV_SECRET_MOUNT_POINT}/{settings.PROJECT_NAME}-{self.track}",
                )
                secrets = self.client.secrets.kv.v1.read_secret(
                    path=f"{settings.PROJECT_NAME}-{self.track}",
                    mount_point=settings.VAULT_KV_SECRET_MOUNT_POINT,
                )
                secrets_list = secrets["data"]
            except hvac.exceptions.InvalidPath as e:
                logger.error(
                    icon=f"{self.ICON} 🔑",
                    message="Secrets not found ",
                    error=e,
                    raise_exception=False,
                )
            return secrets_list
        return {}
