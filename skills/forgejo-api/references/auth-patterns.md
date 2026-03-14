# Auth Patterns — forgejo-cli

Complete, working authentication patterns for all 3 auth methods. Read this file when constructing curl commands that require authentication.

OAuth2 access tokens from Forgejo's OAuth2 provider work with the same `Authorization: Bearer $TOKEN` header — use `token-cmd` to retrieve them.

---

## Section 1: Config File Format

The config file lives at `~/.claude/forgejo-cli.local.md`. Claude reads it with the Read tool. It stores pointers to secrets — never secrets themselves. This file is gitignored and user-created at setup time.

```yaml
---
forgejo_url: https://forgejo.example.org
auth_method: token-cmd      # token-cmd | op | env
# token-cmd: any command that outputs a token to stdout
token_cmd: "op item get my-forgejo --fields password --reveal"
# op: 1Password direct integration
op_item: my-forgejo
op_username_field: username   # field ID, NOT the display label
op_password_field: password   # field ID, NOT the display label
---
```

---

## Section 2: How Claude Reads the Config

Read the file with the Read tool, then parse fields using bash:

```bash
# Parse a field from YAML frontmatter using bash:
FORGEJO_URL=$(grep "^forgejo_url:" ~/.claude/forgejo-cli.local.md | sed 's/^forgejo_url: *//' | tr -d '"'"'" )
AUTH_METHOD=$(grep "^auth_method:" ~/.claude/forgejo-cli.local.md | sed 's/^auth_method: *//' | tr -d '"'"'" | sed 's/#.*//' | tr -d ' ')
```

**Note:** The `.local.md` file should contain ONLY YAML frontmatter between `---` delimiters. Do not add markdown content below the closing `---`. Anything after the closing delimiter is ignored by the parser and may cause unexpected grep results.

---

## Section 3: token-cmd Auth (Happy Path)

The preferred method — works with any secret manager.

```bash
# Read token_cmd from config
TOKEN_CMD=$(grep "^token_cmd:" ~/.claude/forgejo-cli.local.md | sed 's/^token_cmd: *//' | sed 's/^"\(.*\)"$/\1/')
# Execute it to get the token (set +x prevents trace leakage)
# Trust boundary: token_cmd is user-configured — it runs with the same privilege as any
# shell alias or .envrc command. The command value is logged (not the token) so the user
# can verify what is being invoked.
set +x
TOKEN=$(eval "$TOKEN_CMD")
if [ -z "$TOKEN" ]; then echo "Error: token_cmd produced no output" >&2; return; fi
# Use in curl
curl -s -w '\n%{http_code}' \
  --connect-timeout 10 --max-time 30 \
  -H "Authorization: token $TOKEN" \
  "${FORGEJO_URL}/api/v1/user"
```

Note: log the token_cmd value (not the token) so the user can verify what's being called.

---

## Section 4: 1Password (op) Auth

Complete pattern for op auth — basic auth via process substitution:

```bash
# Read op config
OP_ITEM=$(grep "^op_item:" ~/.claude/forgejo-cli.local.md | sed 's/^op_item: *//' | tr -d '"')
OP_USER_FIELD=$(grep "^op_username_field:" ~/.claude/forgejo-cli.local.md | sed 's/^op_username_field: *//' | tr -d '"')
OP_PASS_FIELD=$(grep "^op_password_field:" ~/.claude/forgejo-cli.local.md | sed 's/^op_password_field: *//' | tr -d '"')
: "${OP_USER_FIELD:=username}"
: "${OP_PASS_FIELD:=password}"

# Resolve credentials (set +x prevents trace leakage)
set +x
OP_USER=$(op item get "$OP_ITEM" --fields "$OP_USER_FIELD" --reveal)
OP_PASS=$(op item get "$OP_ITEM" --fields "$OP_PASS_FIELD" --reveal)
HOST=$(echo "$FORGEJO_URL" | sed 's|https\?://||' | sed 's|/.*||')

# Validate credentials contain no newlines (would break netrc format)
if [[ "$OP_USER" == *$'\n'* ]] || [[ "$OP_PASS" == *$'\n'* ]]; then
  echo "Error: credential contains newline — check 1Password field" >&2
  return 1
fi

# CRITICAL: use --netrc-file with process substitution, NEVER curl -u
curl -s -w '\n%{http_code}' \
  --connect-timeout 10 --max-time 30 \
  --netrc-file <(echo "machine $HOST login $OP_USER password $OP_PASS") \
  "${FORGEJO_URL}/api/v1/user"
```

IMPORTANT: The process substitution `<(echo ...)` MUST appear inline in the curl command. It cannot be captured as a variable. This is why there is no auth helper script — Claude must construct the full curl command directly.

---

## Section 5: env Var Auth

Least preferred — env vars visible to child processes.

```bash
# Least preferred — env vars visible to child processes
TOKEN="${FORGEJO_TOKEN:-}"
if [ -z "$TOKEN" ]; then
  echo "Error: FORGEJO_TOKEN not set" >&2
  exit 1
fi
curl -s -w '\n%{http_code}' \
  --connect-timeout 10 --max-time 30 \
  -H "Authorization: token $TOKEN" \
  "${FORGEJO_URL}/api/v1/user"
```

---

## Section 6: Canonical Curl Pattern

The template every API call follows — no deviation:

```bash
response=$(curl -s -w '\n%{http_code}' \
  --connect-timeout 10 --max-time 30 \
  <auth arguments inline here> \
  -H "Content-Type: application/json" \
  "${FORGEJO_URL}/api/v1/<endpoint>")
http_code=$(echo "$response" | tail -1)
body=$(echo "$response" | sed '$d')
```

Always check http_code before parsing body. Error classification:

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

## Section 7: Token Creation (Special Case)

Creating an API token always requires basic auth — even if you have a token already:

```bash
# Process substitution required — token creation endpoint only accepts basic auth
curl -s -w '\n%{http_code}' \
  --netrc-file <(echo "machine $HOST login $USER password $PASS") \
  -H "Content-Type: application/json" \
  -d '{"name":"my-token","scopes":["write:repository","write:issue"]}' \
  "${FORGEJO_URL}/api/v1/users/${USER}/tokens"
```

---

## Section 8: 2FA and Sudo Headers

```bash
# 2FA: add OTP header if account has 2FA enabled
-H "X-Forgejo-OTP: 123456"

# Admin sudo: act as another user
-H "Sudo: targetusername"
# or
"${FORGEJO_URL}/api/v1/endpoint?sudo=targetusername"
```
