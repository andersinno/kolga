from datetime import datetime, timedelta
from typing import Dict

import hvac  # type: ignore
from jwt import encode

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

    def login(
        self,
        ci_jwt: str = settings.VAULT_JWT,
        ci_jwt_private_key: str = settings.VAULT_JWT_PRIVATE_KEY,
    ) -> None:
        if self.initialized:
            try:
                secret_path = f"{settings.PROJECT_NAME}-{self.track}"
                print(f"JWT token: {ci_jwt}")
                if ci_jwt_private_key:
                    print("Generating JWT token")
                    ci_jwt = encode(
                        {
                            "user": secret_path,
                            "aud": secret_path,
                            "exp": datetime.utcnow() + timedelta(seconds=60),
                            "iat": datetime.utcnow(),
                        },
                        ci_jwt_private_key.replace("\\n", "\n"),
                        algorithm="RS256",
                    )
                print(f"JWT token: {ci_jwt}")
                response = self.client.auth.jwt.jwt_login(
                    role=secret_path,
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
            secret_path = f"{settings.PROJECT_NAME}-{self.track}"
            try:
                logger.info(
                    icon=f"{self.ICON} 🔑",
                    message=f"Checking for secrets in {settings.VAULT_KV_SECRET_MOUNT_POINT}/{secret_path}",
                )
                secrets = {}
                if settings.VAULT_KV_VERSION == 2:
                    secrets = self.client.secrets.kv.read_secret_version(
                        path=secret_path,
                        mount_point=settings.VAULT_KV_SECRET_MOUNT_POINT,
                    )
                    secrets_list = secrets["data"]["data"]

                else:
                    secrets = self.client.secrets.kv.v1.read_secret(
                        path=secret_path,
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
