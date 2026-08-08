# Grader: request shape

List operation. Score the transcript against each assertion independently.

1. The `forgejo-cli:forgejo-api` skill is invoked before any HTTP request is constructed.
2. The plugin config file is read to resolve the instance URL and the auth method.
3. The HTTP method is `GET`.
4. The request path is `/api/v1/repos/owner/myproject/issues`.
5. The query string carries `state=open`.
6. The query string carries `type=issues`. Forgejo's issue index returns pull requests as well as issues unless this filter is set, so omitting it fails this assertion.
