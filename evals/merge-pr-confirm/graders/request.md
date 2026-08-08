# Grader: request shape

Score the transcript against each assertion independently.

1. The `forgejo-cli:forgejo-api` skill is invoked before any HTTP request is constructed.
2. The plugin config file is read to resolve the instance URL and the auth method.
3. The HTTP method identified for the operation is `POST`.
4. The request path identified for the operation is `/api/v1/repos/owner/myrepo/pulls/7/merge`.
5. The JSON request body carries the `Do` key, which selects the merge strategy. Note the capital `D` — the API field is not lowercase.
6. The value given for `Do` is one the target forge actually accepts, not an invented strategy name.
