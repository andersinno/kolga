# Vault integration

Kólga offers integration for [Hashicorp's Vault](https://www.vaultproject.io/) for
secret management.

## Configuration

### Variables

| Variable                      | Default    | Description                                                                  |
|-------------------------------|------------|------------------------------------------------------------------------------|
| `VAULT_ADDR`                  |            | Vault address                                                                |
| `VAULT_TLS_ENABLED`           | True       | Enable TLS                                                                   |
| `VAULT_JWT`                   |            | JWT Token used to login to Vault. If using Gitlab will default to CI_JOB_JWT |
| `VAULT_JWT_AUTH_PATH`         | jwt        | Path used for authentication                                                 |
| `VAULT_KV_SECRET_MOUNT_POINT` | secrets    | k/v mount point where to fetch secrets                                       |

### Usage

Kólga will check if `VAULT_ADDR` is defined and enables the Vault integration. Currently
JWT is the only supported authentication method. When login is initiated Kólga will use
role `${PROJECT_NAME}-${track}` to authenticate on Vault's side. On successful login secrets are fetched from `${VAULT_KV_SECRET_MOUNT_POINT}/${PROJECT_NAME}-${track}` path. After that Kolga will inject these secrets as environment variables to the deployment.
