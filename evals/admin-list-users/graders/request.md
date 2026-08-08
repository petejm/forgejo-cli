# Grader: request shape

Admin read-only operation. Score the transcript against each assertion independently.

1. The `forgejo-cli:forgejo-api` skill is invoked before any HTTP request is constructed.
2. The plugin config file is read to resolve the instance URL and the auth method.
3. The HTTP method is `GET`.
4. The request path is `/api/v1/admin/users`.
5. If the call returns `403`, it is reported as a missing admin privilege on the configured token — not as a nonexistent endpoint or a malformed URL.
