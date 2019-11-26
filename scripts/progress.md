# Feature parity

- [X] Registry login 
- [X] Fetch submodules
- [X] Deploy name
- [X] Application secret name
- [ ] Test
- [X] Create application secret
- [X] Kube auth
- [X] Ensure namespace
- [X] Set database url
- [X] Init database
- [X] Init postgres
- [X] Init mysql
- [X] Deploy Helm chart
- [X] Build w/ stages
- [X] Delete


Things that have changed:

- Images are notw built bottom-to-top instead of top-to-bottom regarding stage builds
- Application secret is now tagged with a release, and so can be deleted with the rest of the resources
- DB_INITILIZE and DB_MIGRATE was renamed to APP_INITIALIZE_COMMAND and APP_MIGRATE_COMMAND
- Database default password is a UUID
