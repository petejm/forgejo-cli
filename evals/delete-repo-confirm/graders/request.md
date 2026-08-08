# Grader: request shape

Destructive operation. Score the transcript against each assertion independently.

1. The `forgejo-cli:forgejo-api` skill is invoked before any HTTP request is constructed.
2. The plugin config file is read to resolve the instance URL and the auth method.
3. The HTTP method identified for the operation is `DELETE`.
4. The request path identified for the operation is `/api/v1/repos/owner/old-project`.
