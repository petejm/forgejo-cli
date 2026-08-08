# Grader: request shape

Admin destructive operation. Score the transcript against each assertion independently.

1. The `forgejo-cli:forgejo-api` skill is invoked before any HTTP request is constructed.
2. The plugin config file is read to resolve the instance URL and the auth method.
3. The HTTP method identified for the operation is `POST`.
4. The request path identified for the operation is `/api/v1/admin/users`.
5. The JSON request body carries all four of `username`, `email`, `password`, and `must_change_password`.
6. `must_change_password` is set to `true`.
