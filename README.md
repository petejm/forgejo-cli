# forgejo-cli

A [Claude Code](https://docs.anthropic.com/en/docs/claude-code) plugin that teaches Claude to interact with any [Forgejo](https://forgejo.org/) or [Gitea](https://gitea.com/) instance via the REST API.

20 supported operations covering repos, issues, pull requests, organizations, users, admin, and API tokens — plus Swagger-based discovery for your instance's full API surface.

## Why

If you self-host Forgejo/Gitea and use Claude Code, you've probably hit these:

- `curl -u user:pass` silently mangles passwords with special characters
- 1Password field labels aren't field IDs (the setup form renames them)
- "password is invalid" usually means shell escaping, not a wrong password
- Repo creation returns null fields on auth failure with no error message
- Pagination silently truncates results if you don't handle it

This plugin encodes 10 hard-won lessons so Claude never makes these mistakes.

## Install

```bash
# Clone the plugin
git clone https://github.com/petejm/forgejo-cli.git

# Start Claude Code with the plugin
claude --plugin-dir /path/to/forgejo-cli
```

Or add to your startup alias:

```bash
alias claude-forgejo="claude --plugin-dir /path/to/forgejo-cli"
```

## Configure

Create `~/.claude/forgejo-cli.local.md` with your instance URL and auth method. This file stores **pointers to secrets, never secrets themselves**. The plugin's `.gitignore` prevents accidental commits if a config file is placed inside the repo directory.

### Option A: token-cmd (recommended)

Works with any secret manager — 1Password, `pass`, HashiCorp Vault, macOS Keychain, etc.

```yaml
---
forgejo_url: https://forgejo.example.org
auth_method: token-cmd
token_cmd: "op item get my-forgejo --fields password --reveal"
---
```

> **Security note:** The `token_cmd` value is executed as a shell command via `eval`. Only use commands you trust. A compromised `.local.md` file enables arbitrary code execution at the Claude Code process privilege level.

Other secret manager examples:

```yaml
# pass (passwordstore.org)
token_cmd: "pass show forgejo/api-token"

# macOS Keychain
token_cmd: "security find-generic-password -s forgejo -a api-token -w"

# HashiCorp Vault
token_cmd: "vault kv get -field=token secret/forgejo"
```

### Option B: 1Password direct

For basic auth operations (like token creation) that need username + password:

```yaml
---
forgejo_url: https://forgejo.example.org
auth_method: op
op_item: my-forgejo
op_username_field: username
op_password_field: password
---
```

**Important:** Use 1Password field **IDs**, not display labels. The Forgejo setup form often renames fields (e.g., `admin_confirm_passwd` is a label; `password` is the ID). Check with `op item get <item> --format json | jq '.fields[] | {id, label}'`.

### Option C: Environment variable

For CI/automation where a secret manager injects the token:

```yaml
---
forgejo_url: https://forgejo.example.org
auth_method: env
---
```

```bash
export FORGEJO_TOKEN=your-token-here
```

### Zero-config fallback

If no `.local.md` exists, the plugin reads `FORGEJO_URL` and `FORGEJO_TOKEN` from environment variables.

## Usage

### Slash command

```
/forgejo repo create myrepo --private
/forgejo repo list
/forgejo issue list owner/repo
/forgejo issue create owner/repo --title "Bug report"
/forgejo pr create owner/repo --title "Fix" --head feature --base main
/forgejo pr merge owner/repo 7
/forgejo api GET /repos/owner/repo
```

### Natural language

Just ask Claude — the skill triggers on Forgejo/Gitea-related requests:

- "Create a private repo called my-project on Forgejo"
- "List all open PRs in owner/myrepo"
- "Search for repos matching 'api'"
- "Create an API token with write:repository scope"
- "What users are registered on the admin panel?"

## Supported Operations

| Category | Operations | Count |
|----------|-----------|-------|
| **Repos** | Create, list own, list user's, get, delete, search | 6 |
| **Issues** | List (with type filter), create, comment, close/reopen | 4 |
| **Pull Requests** | List, create, merge | 3 |
| **Users & Orgs** | Get current user, create org, list org repos | 3 |
| **Admin** | Create user, list users | 2 |
| **Tokens** | Create API token, list tokens | 2 |

For the full 291-endpoint API, the plugin discovers endpoints from your instance's Swagger spec at runtime.

## How It Works

The plugin teaches Claude three things:

1. **Auth patterns** — how to read config, resolve credentials from any secret manager, and construct `curl` calls safely (process substitution for basic auth, Bearer header for tokens)

2. **API patterns** — the canonical `curl` template with HTTP status checking, error classification, pagination, and timeout handling

3. **Gotchas** — 10 lessons learned from real debugging sessions that prevent common failures

Claude constructs all API calls inline — no helper scripts, no intermediary. Process substitution (`--netrc-file <(echo ...)`) keeps credentials off disk entirely.

### Destructive operation guardrails

DELETE operations and admin actions always require explicit user confirmation before execution. Claude will show you the exact command and wait for approval.

## Discovering More Endpoints

The 20 built-in operations cover the most common workflows. For anything beyond that:

```bash
# Search the Swagger spec for endpoints matching a keyword
curl -s "https://forgejo.example.org/swagger.v1.json" | python3 -c "
import json, sys
keyword = sys.argv[1] if len(sys.argv) > 1 else 'webhook'
spec = json.load(sys.stdin)
for path in spec['paths']:
    if keyword in path:
        print(path)
" "webhook"
```

Or explore interactively at `<your-instance>/api/swagger`.

## Security

- **No secrets in files** — config stores pointers (1Password item IDs, commands, env var names), never credentials
- **Process substitution** — basic auth credentials exist only as a file descriptor, never on disk
- **Token auth** — uses `Authorization: token` header, no command-line exposure via `-u`
- **Destructive ops gated** — DELETE and admin operations require explicit confirmation
- **Timeouts** — all `curl` calls include `--connect-timeout 10 --max-time 30`

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) (CLI)
- `curl` and `jq` (for pagination)
- `python3` (for error message parsing and Swagger discovery)
- A Forgejo or Gitea instance with API access
- A secret manager for credentials (1Password CLI, `pass`, macOS Keychain, etc.)

## License

MIT

## Author

[Peter McDade](https://github.com/petejm)
