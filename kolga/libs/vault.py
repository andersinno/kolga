import os
from datetime import datetime, timedelta
from tempfile import mkstemp
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
                if ci_jwt_private_key:
                    ci_jwt = encode(
                        {
                            "user": secret_path,
                            "aud": secret_path,
                            "exp": datetime.utcnow() + timedelta(seconds=60),
                            "iat": datetime.utcnow(),
                        },
                        ci_jwt_private_key,
                        algorithm="RS256",
                    )
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

    def _read_tf_secrets(
        self, secret_path: str, secrets_list: Dict[str, str]
    ) -> Dict[str, str]:
        logger.info(
            icon=f"{self.ICON} 🔑",
            message=f"Checking for secrets in {settings.VAULT_KV_SECRET_MOUNT_POINT}/{secret_path}-tf",
        )
        tf_secrets = self.client.secrets.kv.read_secret_version(
            path=f"{secret_path}-tf",
            mount_point=settings.VAULT_KV_SECRET_MOUNT_POINT,
        )
        # Check for duplicates and remove duplicate secret from tf secrets.
        for key in list(tf_secrets["data"]["data"]):
            if key in secrets_list:
                tf_secrets["data"]["data"].pop(key)
        secrets_list.update(tf_secrets["data"]["data"])
        return secrets_list

    def _create_file_secrets(self, key: str, value: str) -> None:
        logger.info(
            icon=f"{self.ICON} 🔑",
            message=f"Found secret with K8S_FILE_SECRET prefix {key}. Creating file type secret",
        )
        file_secret_path = (
            settings.active_ci.VALID_FILE_SECRET_PATH_PREFIXES[0]
            if settings.active_ci
            else "/tmp/"
        )
        fp, name = mkstemp(dir=file_secret_path)
        with os.fdopen(fp, "w") as f:
            f.write(value)
            os.environ[key.upper()] = name

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

                # Check secrets defined by Terraform
                if settings.VAULT_TF_SECRETS and settings.VAULT_KV_VERSION == 2:
                    secrets_list = self._read_tf_secrets(secret_path, secrets_list)

                # Check for file type secrets
                for key, value in list(secrets_list.items()):
                    if key.startswith(settings.K8S_FILE_SECRET_PREFIX):
                        secrets_list.pop(key)
                        self._create_file_secrets(key, value)

            except hvac.exceptions.InvalidPath as e:
                logger.error(
                    icon=f"{self.ICON} 🔑",
                    message="Secrets not found ",
                    error=e,
                    raise_exception=False,
                )
            return secrets_list
        return {}
