# Changelog

## [v3]
### Added
- new configuration variable VAULT_PROJECT_SECRET_NAME, change VAULT_KV_SECRET_MOUNT_POINT's default value to "project_secrets" (2021-05-07)
- add support for enabling prometheus operator to discover application level metrics (2021-05-04)
- support ingress api versions extensions/v1beta1, networking.k8s.io/v1beta1 and networking.k8s.io/v1 (2021-05-03)
- add feature that allows Vault module to create file type secrets from Vault secrets that has prefix K8S_FILE_SECRET_ (2021-04-13)
- allow reading of Vault secrets from two paths and merge to one (2021-04-13)
- add SONARQUBE_DISABLED settings for GitLab template for disabling Sonarqube scans (2021-04-07)
- add debug logging, enabled by KOLGA_DEBUG (2012-03-30)
- move network policy creation into the helm chart (2010-03-24)
- add plugin support (2021-02-05)
- add Sentry plugin (2021-02-05)
- add Slack plugin (2021-02-05)
- whitelist-source-range annotation for ingress (2021-01-04)
