import os

import pytest
from pytest import MonkeyPatch

from kolga.libs.vault import Vault
from kolga.settings import settings

os.environ["VAULT_TOKEN"] = "roottoken"
vault_addr = os.environ.get("VAULT_ADDR", "")
expected_secrets = {"key": "test", "value": 1, "DUPLICATE": "user-secret"}
expected_tf_secrets = {"tf_secret": "test", "DUPLICATE": "terraform-secret"}


@pytest.mark.vault
def test_vault_init() -> None:
    vault = Vault(track="review", vault_addr=vault_addr)
    assert vault.initialized


@pytest.mark.vault
def test_get_secrets_v1(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "VAULT_KV_VERSION", 1)
    monkeypatch.setattr(settings, "VAULT_KV_SECRET_MOUNT_POINT", "secrets")
    monkeypatch.setattr(settings, "PROJECT_NAME", "test")
    vault = Vault(track="review", vault_addr=vault_addr)
    vault.client.sys.enable_secrets_engine(
        backend_type="kv", path="secrets", options={"version": "1"}
    )
    vault.client.secrets.kv.v1.create_or_update_secret(
        path="test-review",
        mount_point="secrets",
        secret=expected_secrets,
    )
    secrets = vault.get_secrets()
    assert secrets == expected_secrets


@pytest.mark.vault
def test_get_secrets_v2(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "VAULT_KV_SECRET_MOUNT_POINT", "secret")
    monkeypatch.setattr(settings, "PROJECT_NAME", "test")
    vault = Vault(track="review", vault_addr=vault_addr)
    vault.client.secrets.kv.v2.create_or_update_secret(
        path="test-review",
        mount_point="secret",
        secret=expected_secrets,
    )
    secrets = vault.get_secrets()
    assert secrets == expected_secrets


@pytest.mark.vault
def test_get_tf_secrets(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "VAULT_TF_SECRETS", True)
    monkeypatch.setattr(settings, "VAULT_KV_SECRET_MOUNT_POINT", "secret")
    monkeypatch.setattr(settings, "PROJECT_NAME", "test")
    vault = Vault(track="review", vault_addr=vault_addr)
    vault.client.secrets.kv.v2.create_or_update_secret(
        path="test-review",
        mount_point="secret",
        secret=expected_secrets,
    )
    vault.client.secrets.kv.v2.create_or_update_secret(
        path="test-review-tf",
        mount_point="secret",
        secret=expected_tf_secrets,
    )
    secrets = vault.get_secrets()
    assert len(secrets) == 4
    assert "user-secret" in secrets.values()


@pytest.mark.vault
def test_file_type_secrets(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "VAULT_KV_SECRET_MOUNT_POINT", "secret")
    monkeypatch.setattr(settings, "PROJECT_NAME", "test")
    vault = Vault(track="review", vault_addr=vault_addr)
    expected_secrets = {"K8S_FILE_SECRET_TEST": "test"}
    vault.client.secrets.kv.v2.create_or_update_secret(
        path="test-review",
        mount_point="secret",
        secret=expected_secrets,
    )
    vault.get_secrets()
    secret = os.environ.get("K8S_FILE_SECRET_TEST", "")
    with open(secret) as f:
        file_content = f.read()
    assert file_content == "test"
