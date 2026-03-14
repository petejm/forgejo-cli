---
name: forgejo-api
description: |
  Interact with Forgejo and Gitea REST APIs — create repos, manage issues and PRs,
  administer users and orgs, search, and more. Use this skill whenever the user mentions
  Forgejo, Gitea, self-hosted git, or needs to interact with a Forgejo/Gitea instance API.
  Also trigger when you see Forgejo URLs, repo creation on self-hosted servers, or the
  user asks about alternatives to GitHub/GitLab for self-hosted git. Trigger phrases:
  'forgejo', 'gitea', 'forgejo api', 'create repo on forgejo', 'self-hosted git api',
  'forgejo issue', 'forgejo pr', 'forgejo admin'.
---

# forgejo-api Skill

Teaches Claude to interact with any Forgejo or Gitea instance via the REST API. Covers auth, API calls, error handling, pagination, and known failure modes.

---

## Section 1: Configuration

Config file location: `~/.claude/forgejo-cli.local.md`

Read this file with the Read tool at the start of every session. If it does not exist, fall back to `FORGEJO_URL` and `FORGEJO_TOKEN` env vars (zero-config path for quick use).

**Fields:**

- `forgejo_url` — required, base URL of the Forgejo instance (no trailing slash)
- `auth_method` — `token-cmd` (preferred), `op`, or `env`
- For `token-cmd`: also set `token_cmd` — any command outputting a token to stdout
- For `op`: also set `op_item`, `op_username_field`, `op_password_field`
- For `env`: set `FORGEJO_TOKEN` in the environment

**Minimal configs:**

```yaml
# token-cmd (preferred)
---
forgejo_url: https://forgejo.example.org
auth_method: token-cmd
token_cmd: "op item get my-item --fields password --reveal"
---
```

```yaml
# op (1Password direct)
---
forgejo_url: https://forgejo.example.org
auth_method: op
op_item: my-item
op_username_field: username
op_password_field: password
---
```

```yaml
# env (CI/automation)
---
forgejo_url: https://forgejo.example.org
auth_method: env
---
```

See `references/auth-patterns.md` for complete setup examples with all fields.

---

## Section 2: Authentication

Auth flow in 4 steps:

**Step 1:** Read config with the Read tool on `~/.claude/forgejo-cli.local.md`.

**Step 2:** Resolve credentials using the Bash tool:
- `token-cmd`: parse `token_cmd` from config, eval it with `set +x` to suppress trace
- `op`: call `op item get` with the configured item and field IDs
- `env`: read `FORGEJO_TOKEN` from the environment

**Step 3:** Construct the curl command **inline** with auth arguments.

**CRITICAL RULE**: Process substitution `<(echo ...)` MUST appear inline in the curl command. It cannot be captured as a shell variable or passed as an argument. Always construct the complete curl command in a single Bash invocation.

Quick auth patterns (full examples in `references/auth-patterns.md`):
- token-cmd/env: `-H "Authorization: token $TOKEN"`
- op basic auth: `--netrc-file <(echo "machine $HOST login $USER password $PASS")`

**Step 4:** Check the HTTP status code before treating credentials as valid. If credentials resolve but the API returns 401, re-read gotchas #1 and #3 before resetting passwords.

---

## Section 3: Making API Calls

Every API call follows this canonical pattern — no deviation:

```bash
response=$(curl -s -w '\n%{http_code}' \
  -H "Authorization: token $TOKEN" \
  -H "Content-Type: application/json" \
  "${FORGEJO_URL}/api/v1/<endpoint>")
http_code=$(echo "$response" | tail -1)
body=$(echo "$response" | sed '$d')

# Always check status before parsing
if [[ "$http_code" != "200" && "$http_code" != "201" && "$http_code" != "204" ]]; then
  echo "API error $http_code: $(echo "$body" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("message","unknown"))')" >&2
  exit 1
fi
```

**Error classification:**

| Code | Meaning | Action |
|------|---------|--------|
| 200/201/204 | Success | Parse body |
| 401 | Auth failure | Check credentials and token scopes — also check for shell escaping (gotcha #1/#3) |
| 403 | Forbidden | Check permissions and token scopes |
| 404 | Not found | Check URL construction and resource names |
| 409 | Conflict | Resource already exists — handle as idempotent, not error |
| 422 | Validation error | Check request body structure |
| 429 | Rate limited | Back off and retry |

---

## Section 4: Supported Operations

20 operations organized by tag. See `references/endpoints.md` for full curl patterns and body fields.

**Repos:**
- `POST /api/v1/user/repos` — create repo
- `GET /api/v1/user/repos` — list own repos
- `GET /api/v1/users/{username}/repos` — list user's repos
- `GET /api/v1/repos/{owner}/{repo}` — get repo
- `DELETE /api/v1/repos/{owner}/{repo}` — delete repo (DESTRUCTIVE)
- `GET /api/v1/repos/search?q={query}` — search repos

**Issues:**
- `GET /api/v1/repos/{owner}/{repo}/issues` — list issues
- `POST /api/v1/repos/{owner}/{repo}/issues` — create issue
- `POST /api/v1/repos/{owner}/{repo}/issues/{index}/comments` — comment on issue
- `PATCH /api/v1/repos/{owner}/{repo}/issues/{index}` — close/reopen issue

**Pull Requests:**
- `GET /api/v1/repos/{owner}/{repo}/pulls` — list PRs
- `POST /api/v1/repos/{owner}/{repo}/pulls` — create PR
- `POST /api/v1/repos/{owner}/{repo}/pulls/{index}/merge` — merge PR

**Users & Orgs:**
- `GET /api/v1/user` — get current user (auth verification)
- `POST /api/v1/orgs` — create org
- `GET /api/v1/orgs/{org}/repos` — list org repos

**Admin (DESTRUCTIVE — confirm before executing):**
- `POST /api/v1/admin/users` — create user
- `GET /api/v1/admin/users` — list users

**Tokens (requires basic auth even with a token):**
- `POST /api/v1/users/{username}/tokens` — create API token
- `GET /api/v1/users/{username}/tokens` — list tokens

---

## Section 5: Pagination

Forgejo uses `page` + `limit` query params and a `x-total-count` response header. Default page size 30, max 50.

```bash
page=1
all_results="[]"
while true; do
  response=$(curl -s -w '\n%{http_code}' \
    -H "Authorization: token $TOKEN" \
    "${FORGEJO_URL}/api/v1/<endpoint>?page=$page&limit=50")
  http_code=$(echo "$response" | tail -1)
  body=$(echo "$response" | sed '$d')
  [[ "$http_code" != "200" ]] && { echo "Error $http_code" >&2; exit 1; }
  count=$(echo "$body" | python3 -c "import json,sys; print(len(json.load(sys.stdin)))")
  all_results=$(printf '%s\n%s' "$all_results" "$body" | python3 -c "import json,sys; data=sys.stdin.read(); parts=[json.loads(p) for p in data.strip().split('\n') if p.strip()]; print(json.dumps(sum(parts,[])))" 2>/dev/null || echo "$body")
  [[ "$count" -lt 50 ]] && break
  page=$((page + 1))
done
```

Note: use jq if available (`command -v jq`) as it's cleaner for JSON accumulation. Fall back to python3 otherwise.

---

## Section 6: Gotchas

These 10 lessons are hard-won. Read carefully before debugging auth or API failures.

1. **Never `curl -u user:pass`** — use `--netrc-file <(echo "machine $host login $user password $pass")` (process substitution). Passwords with special characters get shell-mangled before curl sees them.

2. **1Password field LABELS are not field IDs** — the setup form renames them (e.g., "admin_confirm_passwd" is a label; "password" is the field ID). Always use `--fields` with the field ID, not the display label.

3. **"password is invalid" from Forgejo API often means shell escaping broke the password**, not that the password is wrong. Check the auth pattern before resetting credentials.

4. **Process substitution `<(echo ...)` creates a file descriptor**, not a file on disk. Credentials never touch the filesystem. This is preferred over temp files — no cleanup required, no race condition window.

5. **Repo creation returns null fields on auth failure** — always check HTTP status code (`-w '%{http_code}'`) before parsing the response body. A 401 with null JSON looks like success until you try to use the repo URL.

6. **"repo already exists" is HTTP 409** — handle it gracefully, not as an error. In most workflows this is an idempotent condition, not a failure.

7. **`--exit-code` is not a valid `git ls-remote` flag** — it's a `git diff` flag. Common copy-paste error that produces a confusing "unknown switch" message.

8. **Pagination**: Forgejo uses Link header + `x-total-count`. Default page size 30, max 50. Always handle pagination for list operations or you silently miss results.

9. **2FA**: if enabled on the account, add `X-Forgejo-OTP: <code>` header to all requests. Without it, 2FA-protected accounts return 401 with no useful message.

10. **Admin sudo**: act as another user via `?sudo=username` query parameter or `Sudo:` header. Requires an admin token — does not work with regular user tokens.

---

## Section 7: Discovery

For endpoints not in the supported 20, the Forgejo Swagger spec is the authoritative source.

```bash
# Find endpoints matching a keyword
curl -s "${FORGEJO_URL}/swagger.v1.json" | python3 -c "
import json, sys, re
keyword = 'release'  # change this
spec = json.load(sys.stdin)
for path, methods in spec['paths'].items():
    if keyword in path or any(keyword in str(op) for op in methods.values()):
        print(path)
"

# Get full operation details
curl -s "${FORGEJO_URL}/swagger.v1.json" | python3 -c "
import json, sys
spec = json.load(sys.stdin)
print(json.dumps(spec['paths']['/api/v1/repos/{owner}/{repo}/releases']['post'], indent=2))
"
```

Forgejo's web UI has a Swagger explorer at `<forgejo_url>/api/swagger`. Useful for interactive exploration before scripting.

---

## Section 8: Destructive Operations

For all DELETE methods and admin operations that modify or remove user, org, or repo state:

1. Tell the user what will happen in plain language
2. Show the exact curl command that will run (with credentials redacted — show `[TOKEN]` or `[PASSWORD]`)
3. Wait for explicit user confirmation ("yes", "proceed", "do it", etc.)
4. Execute only after confirmation is given

This applies even when the instruction seems unambiguous. Destructive operations are never batched or assumed. When in doubt, confirm.
