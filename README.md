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

### From the marketplace (persists across sessions)

Inside Claude Code:

```
/plugin marketplace add petejm/forgejo-cli
/plugin install forgejo-cli@petejm-plugins
```

The plugin then loads in every future session. Update later with `/plugin marketplace update petejm-plugins` and `/plugin update forgejo-cli`.

### Try it without installing (this session only)

```bash
# Clone the plugin
git clone https://github.com/petejm/forgejo-cli.git ~/src/forgejo-cli

# Start Claude Code with the plugin — the path must be the clone destination above
claude --plugin-dir ~/src/forgejo-cli
```

`--plugin-dir` loads the plugin for the duration of that session only; it installs nothing. To get it on every launch this way, add a startup alias:

```bash
alias claude-forgejo="claude --plugin-dir ~/src/forgejo-cli"
```

## Configure

Create `~/.claude/forgejo-cli.local.md` with your instance URL and auth method. This file stores **pointers to secrets, never secrets themselves**. The plugin's `.gitignore` prevents accidental commits if a config file is placed inside the repo directory.

### Option A: token-cmd (recommended)

Works with any secret manager — 1Password, `pass`, HashiCorp Vault, macOS Keychain, etc.

```yaml
---
forgejo_url: https://forgejo.example.org
auth_method: token-cmd
token_cmd: "op read op://<vault>/<item>/<field>"
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

**Important:** The Forgejo setup form can rename fields, so the label you see is not necessarily what a lookup matches (e.g. an `admin_confirm_passwd` label sitting over a `password` field). Use the documented selector form — `op item get <item> --fields "label=password" --reveal` — and when a lookup comes back empty, inspect the item with `op item get <item> --format json | jq '.fields[] | {id, label}'` to see what is actually there.

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

For the rest of the API, the plugin discovers endpoints from your instance's Swagger spec at runtime.

## How It Works

The plugin teaches Claude three things:

1. **Auth patterns** — how to read config, resolve credentials from any secret manager, and construct `curl` calls safely (process substitution for basic auth, `Authorization: token` header for tokens)

2. **API patterns** — the canonical `curl` template with HTTP status checking, error classification, pagination, and timeout handling

3. **Gotchas** — 10 lessons learned from real debugging sessions that prevent common failures

Claude constructs all API calls inline — no helper scripts, no intermediary. Process substitution (`--netrc-file <(printf 'machine %s login "%s" password "%s"\n' ...)`) hands `curl` an open file descriptor instead of a temp file on systems with `/dev/fd`, which includes Linux and macOS. The `printf` form with quoted values is load-bearing, not stylistic: netrc is whitespace-tokenized, so an unquoted value is silently truncated at the first space.

### Destructive operation guardrails

DELETE operations, merges, and admin actions always require explicit user confirmation before execution. Claude will show you the exact command and wait for approval.

## Discovering More Endpoints

The 20 built-in operations cover the most common workflows. For anything beyond that:

```bash
# Search the Swagger spec for endpoints matching a keyword
curl -s --connect-timeout 10 --max-time 30 "https://forgejo.example.org/swagger.v1.json" | python3 -c "
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
- **Process substitution** — on systems with `/dev/fd` (Linux, macOS), basic auth credentials are passed as an open file descriptor rather than a temp file: nothing to clean up, no race window
- **Token auth** — uses the `Authorization: token` header rather than `-u`. Note the header value is still in `curl`'s argv, so it is visible to `ps` and to CI job logs exactly as `-u` would be. On a shared host, read the header from a file instead — `curl -H @<(printf 'Authorization: token %s\n' "$TOKEN")` keeps it out of the process table.
- **Destructive ops gated** — DELETE, merge, and admin operations require explicit confirmation
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
