# forgejo-cli — Forgejo API Plugin for Claude Code

A Claude Code plugin that teaches Claude to interact with any Forgejo or Gitea instance via the REST API.

---

## Setup

### Step 1 — Install the plugin

Add the plugin directory to your Claude Code startup:

```bash
# Add to your chalk alias or startup script:
claude --plugin-dir ~/work/projects/code_projects/forgejo-cli
```

Or register it in your MCP/plugin config at `~/.claude/settings.json`.

### Step 2 — Create your config file

Create `~/.claude/forgejo-cli.local.md` with your instance config. This file is gitignored and never committed.

**Option A: token-cmd (recommended — works with any secret manager)**

```yaml
---
forgejo_url: https://forgejo.example.org
auth_method: token-cmd
token_cmd: "op item get my-forgejo-item --fields password --reveal"
---
```

**Option B: 1Password direct**

```yaml
---
forgejo_url: https://forgejo.example.org
auth_method: op
op_item: my-forgejo-item
op_username_field: username
op_password_field: password
---
```

**Option C: environment variable (CI/automation)**

```yaml
---
forgejo_url: https://forgejo.example.org
auth_method: env
---
```

```bash
# Set FORGEJO_TOKEN in your environment
export FORGEJO_TOKEN=your-token-here
```

---

## Usage

Use the `/forgejo` command or ask Claude naturally:

```
/forgejo repo create myrepo --private
/forgejo issue list owner/repo
/forgejo pr create owner/repo --title "Fix bug" --head feature --base main
/forgejo api GET /repos/owner/repo
```

Or naturally:

- "Create a private repo called my-project on my Forgejo instance"
- "List all open PRs in owner/myrepo"
- "What users are in the admin panel?"

---

## Supported Operations

| Category | Operations |
|----------|-----------|
| Repos | Create, list own, list user's, get, delete, search |
| Issues | List, create, comment, close/reopen |
| Pull Requests | List, create, merge |
| Users & Orgs | Get current user, create org, list org repos |
| Admin | Create user, list users |
| Tokens | Create API token, list tokens |

Full endpoint reference: `skills/forgejo-api/references/endpoints.md`

---

## Discovering Unsupported Endpoints

```bash
curl -s "${FORGEJO_URL}/swagger.v1.json" | python3 -c "
import json, sys
spec = json.load(sys.stdin)
for path in spec['paths']:
    if 'release' in path:  # change keyword
        print(path)
"
```

Or explore interactively at `<forgejo_url>/api/swagger`.

---

## Auth Notes

- Never use `curl -u user:pass` — passwords with special characters get mangled. Use the process substitution pattern (handled automatically by the skill).
- 1Password field labels are not field IDs. Use field IDs (`username`, `password`) not display labels.
- The `.local.md` config file is gitignored — never committed.
