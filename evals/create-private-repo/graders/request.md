# Grader: request shape

Happy path. Score the transcript against each assertion independently.

1. The `forgejo-cli:forgejo-api` skill is invoked before any HTTP request is constructed.
2. The plugin config file is read to resolve the instance URL and the auth method. Credentials are not invented, guessed, or hard-coded into the command.
3. The HTTP method is `POST`.
4. The request path is `/api/v1/user/repos` — the authenticated-user endpoint. Using `/api/v1/repos` or `/api/v1/admin/repos` fails this assertion.
5. The JSON request body sets `name` to `test-repo` and sets `private` to `true`.
