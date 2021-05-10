# Vault integration

Kólga offers integration for [Hashicorp's Vault](https://www.vaultproject.io/) for
secret management.

## Configuration

### Variables

| Variable                      | Default    | Description                                                                                         |
|-------------------------------|-----------------|-----------------------------------------------------------------------------------------------------|
| `VAULT_ADDR`                  |                 | Vault address                                                                                       |
| `VAULT_JWT`                   |                 | JWT Token used to login to Vault. If using Gitlab will default to CI_JOB_JWT                        |
| `VAULT_JWT_PRIVATE_KEY`       |                 | This can be used to encode your own tokens and pass them to VAULT_JWT                               |
| `VAULT_JWT_AUTH_PATH`         | jwt             | Path used for authentication                                                                        |
| `VAULT_KV_SECRET_MOUNT_POINT` | project_secrets | k/v mount point where to fetch secrets                                                              |
| `VAULT_KV_VERSION`            | 2               | Version of k/v store to use                                                                         |
| `VAULT_PROJECT_SECRET_NAME`   |                 | Non-default secret location under VAULT_KV_SECRET_MOUNT_POINT                                       |
| `VAULT_TF_SECRETS`            | False           | Read additional secrets path (Only supports k/v v2). These secrets are managed by Terraform         |
| `VAULT_TLS_ENABLED`           | True            | Enable TLS                                                                                          |

### Usage

Kólga will check if `VAULT_ADDR` is defined and enables the Vault integration. Currently
JWT is the only supported authentication method. When login is initiated Kólga will use
role `${PROJECT_NAME}-${track}` to authenticate on Vault's side. On successful login secrets are fetched from `${VAULT_KV_SECRET_MOUNT_POINT}/${PROJECT_NAME}-${track}` path. After that Kolga will inject these secrets as environment variables to the deployment. When using a different secret location, the path can be configured using `${VAULT_PROJECT_SECRET_NAME}`.

#### Terraform secrets

If `${VAULT_TF_SECRETS}` is enabled and `${VAULT_KV_VERSION}` is set to 2 Kólga will make additional request to Vault to fetch secrets from `${VAULT_KV_SECRET_MOUNT_POINT}/${PROJECT_NAME}-${track}-tf`. After secrets are fetched it will merge the secrets with `${VAULT_KV_SECRET_MOUNT_POINT}/${PROJECT_NAME}-${track}`and also checks for duplicate keys. If duplicate is found Terraform defined duplicate will be removed and value from `${VAULT_KV_SECRET_MOUNT_POINT}/${PROJECT_NAME}-${track}`will be used.

#### File secrets

Kólga will also check if Vault has secrets starting with prefix `K8S_FILE_SECRET_` and creates file type secret from them.
