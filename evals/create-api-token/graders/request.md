# Grader: request shape

Score the transcript against each assertion independently.

1. The `forgejo-cli:forgejo-api` skill is invoked before any HTTP request is constructed.
2. The plugin config file is read to resolve the instance URL and the auth method.
3. The HTTP method is `POST`.
4. The request path matches `/api/v1/users/<username>/tokens`, with a real username substituted — not a literal placeholder such as `<username>`, `$FORGEJO_USER`, or an empty path segment.
5. The JSON request body carries `name` set to `ci-deploy` and `scopes` including `write:repository`.
6. No user confirmation is requested. Minting a token is additive and individually revocable.
