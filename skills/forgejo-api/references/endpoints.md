# Endpoints Reference — forgejo-cli

20 supported operations with exact endpoint, HTTP method, required request body fields, and example curl snippets. Organized by tag.

Use `$FORGEJO_URL` and `$TOKEN` as placeholders — replace with real values from config and resolved auth.

---

## Repos (6 operations)

### 1. Create repo

`POST /api/v1/user/repos`

Body: `{"name":"<repo>","private":true|false,"description":"<optional>","auto_init":true|false}`

```bash
curl -s -w '\n%{http_code}' \
  --connect-timeout 10 --max-time 30 \
  -H "Authorization: token $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"myrepo","private":true,"auto_init":false}' \
  "${FORGEJO_URL}/api/v1/user/repos"
```

Returns HTTP 201 on success. HTTP 409 if repo already exists (idempotent — not an error).

### 2. List own repos

`GET /api/v1/user/repos?page=1&limit=50`

No body. Returns array of repo objects.

```bash
curl -s -w '\n%{http_code}' \
  --connect-timeout 10 --max-time 30 \
  -H "Authorization: token $TOKEN" \
  "${FORGEJO_URL}/api/v1/user/repos?page=1&limit=50"
```

### 3. List user's repos

`GET /api/v1/users/{username}/repos?page=1&limit=50`

No body.

```bash
curl -s -w '\n%{http_code}' \
  --connect-timeout 10 --max-time 30 \
  -H "Authorization: token $TOKEN" \
  "${FORGEJO_URL}/api/v1/users/someuser/repos?page=1&limit=50"
```

### 4. Get repo

`GET /api/v1/repos/{owner}/{repo}`

No body. Returns single repo object.

```bash
curl -s -w '\n%{http_code}' \
  --connect-timeout 10 --max-time 30 \
  -H "Authorization: token $TOKEN" \
  "${FORGEJO_URL}/api/v1/repos/owner/reponame"
```

### 5. Delete repo

`DELETE /api/v1/repos/{owner}/{repo}`

No body. Returns 204 on success.

**DESTRUCTIVE — requires user confirmation before executing.**

```bash
curl -s -w '\n%{http_code}' \
  --connect-timeout 10 --max-time 30 \
  -X DELETE \
  -H "Authorization: token $TOKEN" \
  "${FORGEJO_URL}/api/v1/repos/owner/reponame"
```

### 6. Search repos

`GET /api/v1/repos/search?q={query}&limit=50`

No body. Returns `{"data": [...], "ok": true}`.

```bash
curl -s -w '\n%{http_code}' \
  --connect-timeout 10 --max-time 30 \
  -H "Authorization: token $TOKEN" \
  "${FORGEJO_URL}/api/v1/repos/search?q=myquery&limit=50"
```

---

## Issues (4 operations)

### 7. List issues

`GET /api/v1/repos/{owner}/{repo}/issues?type=issues&state=open&page=1&limit=50`

Query params: `type` (issues|pulls), `state` (open|closed|all), `labels`, `milestone`, `assignee`.

```bash
curl -s -w '\n%{http_code}' \
  --connect-timeout 10 --max-time 30 \
  -H "Authorization: token $TOKEN" \
  "${FORGEJO_URL}/api/v1/repos/owner/repo/issues?type=issues&state=open&page=1&limit=50"
```

### 8. Create issue

`POST /api/v1/repos/{owner}/{repo}/issues`

Body: `{"title":"<title>","body":"<optional>","assignees":[],"labels":[],"milestone":0}`

```bash
curl -s -w '\n%{http_code}' \
  --connect-timeout 10 --max-time 30 \
  -H "Authorization: token $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"Bug: something broke","body":"Description here"}' \
  "${FORGEJO_URL}/api/v1/repos/owner/repo/issues"
```

### 9. Comment on issue

`POST /api/v1/repos/{owner}/{repo}/issues/{index}/comments`

Body: `{"body":"<comment text>"}`

```bash
curl -s -w '\n%{http_code}' \
  --connect-timeout 10 --max-time 30 \
  -H "Authorization: token $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"body":"My comment here"}' \
  "${FORGEJO_URL}/api/v1/repos/owner/repo/issues/42/comments"
```

### 10. Close issue

`PATCH /api/v1/repos/{owner}/{repo}/issues/{index}`

Body: `{"state":"closed"}` (or `"open"` to reopen)

```bash
curl -s -w '\n%{http_code}' \
  --connect-timeout 10 --max-time 30 \
  -X PATCH \
  -H "Authorization: token $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"state":"closed"}' \
  "${FORGEJO_URL}/api/v1/repos/owner/repo/issues/42"
```

---

## Pull Requests (3 operations)

### 11. List PRs

`GET /api/v1/repos/{owner}/{repo}/pulls?state=open&page=1&limit=50`

```bash
curl -s -w '\n%{http_code}' \
  --connect-timeout 10 --max-time 30 \
  -H "Authorization: token $TOKEN" \
  "${FORGEJO_URL}/api/v1/repos/owner/repo/pulls?state=open&page=1&limit=50"
```

### 12. Create PR

`POST /api/v1/repos/{owner}/{repo}/pulls`

Body: `{"title":"<title>","head":"<branch>","base":"<target>","body":"<optional>"}`

```bash
curl -s -w '\n%{http_code}' \
  --connect-timeout 10 --max-time 30 \
  -H "Authorization: token $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"Fix the bug","head":"feature-branch","base":"main"}' \
  "${FORGEJO_URL}/api/v1/repos/owner/repo/pulls"
```

### 13. Merge PR

`POST /api/v1/repos/{owner}/{repo}/pulls/{index}/merge`

Body: `{"Do":"merge","MergeMessageField":"<optional>"}` (`Do` values: merge, rebase, squash, rebase-merge)

**DESTRUCTIVE — requires user confirmation before executing.**

```bash
curl -s -w '\n%{http_code}' \
  --connect-timeout 10 --max-time 30 \
  -H "Authorization: token $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"Do":"merge"}' \
  "${FORGEJO_URL}/api/v1/repos/owner/repo/pulls/7/merge"
```

---

## Users & Orgs (3 operations)

### 14. Get current user

`GET /api/v1/user`

No body. Good for auth verification.

```bash
curl -s -w '\n%{http_code}' \
  --connect-timeout 10 --max-time 30 \
  -H "Authorization: token $TOKEN" \
  "${FORGEJO_URL}/api/v1/user"
```

### 15. Create org

`POST /api/v1/orgs`

Body: `{"username":"<orgname>","visibility":"public|private","description":"<optional>"}`

```bash
curl -s -w '\n%{http_code}' \
  --connect-timeout 10 --max-time 30 \
  -H "Authorization: token $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"username":"my-org","visibility":"private"}' \
  "${FORGEJO_URL}/api/v1/orgs"
```

### 16. List org repos

`GET /api/v1/orgs/{org}/repos?page=1&limit=50`

```bash
curl -s -w '\n%{http_code}' \
  --connect-timeout 10 --max-time 30 \
  -H "Authorization: token $TOKEN" \
  "${FORGEJO_URL}/api/v1/orgs/my-org/repos?page=1&limit=50"
```

---

## Admin — Read-only (1 operation)

### 17. List users

`GET /api/v1/admin/users?page=1&limit=50`

No body. Requires admin token. Returns array of user objects.

```bash
curl -s -w '\n%{http_code}' \
  --connect-timeout 10 --max-time 30 \
  -H "Authorization: token $TOKEN" \
  "${FORGEJO_URL}/api/v1/admin/users?page=1&limit=50"
```

---

## Admin — Destructive (1 operation) — DESTRUCTIVE — confirm before executing

### 18. Create user

`POST /api/v1/admin/users`

Body: `{"email":"<email>","username":"<username>","password":"<strong-random-password>","must_change_password":true,"source_id":0}`

NOTE: Generate a strong random password — do not hardcode a weak value. Use `openssl rand -base64 18` or similar, and communicate it to the admin out-of-band. `must_change_password: true` ensures the user sets their own password on first login.

**DESTRUCTIVE — requires user confirmation before executing.**

```bash
curl -s -w '\n%{http_code}' \
  --connect-timeout 10 --max-time 30 \
  -H "Authorization: token $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.org","username":"newuser","password":"<generated-strong-password>","must_change_password":true,"source_id":0}' \
  "${FORGEJO_URL}/api/v1/admin/users"
```

---

## Tokens (2 operations)

### 19. Create token

`POST /api/v1/users/{username}/tokens`

Body: `{"name":"<token-name>","scopes":["write:repository","write:issue","write:user"]}`

**NOTE: Requires basic auth (netrc pattern) even if you already have a token.**

```bash
curl -s -w '\n%{http_code}' \
  --connect-timeout 10 --max-time 30 \
  --netrc-file <(echo "machine $HOST login $FORGEJO_USER password $PASS") \
  -H "Content-Type: application/json" \
  -d '{"name":"my-token","scopes":["write:repository","write:issue"]}' \
  "${FORGEJO_URL}/api/v1/users/${FORGEJO_USER}/tokens"
```

### 20. List tokens

`GET /api/v1/users/{username}/tokens`

Also requires basic auth.

```bash
curl -s -w '\n%{http_code}' \
  --connect-timeout 10 --max-time 30 \
  --netrc-file <(echo "machine $HOST login $FORGEJO_USER password $PASS") \
  "${FORGEJO_URL}/api/v1/users/${FORGEJO_USER}/tokens"
```

---

## Swagger Discovery (for operations beyond the 20)

For operations beyond the supported 20, discover endpoints from the instance itself:

```bash
# List all endpoint paths matching a keyword
KEYWORD="webhook"  # change this
curl -s "${FORGEJO_URL}/swagger.v1.json" | python3 -c "
import json, sys
keyword = sys.argv[1] if len(sys.argv) > 1 else 'webhook'
spec = json.load(sys.stdin)
for path, methods in spec['paths'].items():
    if keyword in path or any(keyword in str(op) for op in methods.values()):
        print(path)
" "$KEYWORD"

# Get full operation details including request body schema
curl -s "${FORGEJO_URL}/swagger.v1.json" | python3 -c "
import json, sys
spec = json.load(sys.stdin)
op = spec['paths']['/api/v1/path/here']['post']
print(json.dumps(op, indent=2))
"
```

Also explore interactively at `<forgejo_url>/api/swagger`.
