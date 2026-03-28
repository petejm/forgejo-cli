# forgejo-cli

A Claude Code plugin that teaches Claude to interact with any Forgejo or Gitea instance via the REST API.

## File Structure

```
.claude-plugin/
  plugin.json          — plugin manifest (name, version, keywords, license)
commands/
  forgejo.md           — /forgejo slash command definition
skills/
  forgejo-api/
    SKILL.md           — main skill: auth flow, API call pattern, pagination, gotchas, discovery
    references/
      auth-patterns.md — complete auth examples for all 3 methods (token-cmd, op, env)
      endpoints.md     — 20 supported operations with exact curl snippets
evals/
  evals.json           — eval test cases
README.md              — user-facing documentation
CLAUDE.md              — this file
```

## How to Test

Run evals from the repo root:

```bash
claude eval evals/evals.json
```

The evals cover auth pattern selection, curl construction, pagination, and destructive operation guardrails.

## Contributing

- Keep **gotchas accurate** — every entry in Section 6 of SKILL.md reflects a real failure mode. Only add a gotcha if it's been observed in practice.
- **Test auth patterns** before updating them — especially the `eval "$TOKEN_CMD"` and `--netrc-file <(echo ...)` patterns. These are subtle and easy to break.
- **Never use `echo "$response"`** to split curl output — use `printf '%s\n' "$response"` to preserve trailing newlines correctly when separating body from status code.
- **Destructive operations** (DELETE, admin POST) must always require explicit user confirmation. Do not relax this guardrail.
- Keep `references/endpoints.md` in sync with `SKILL.md` Section 4 — both list the 20 supported operations and their DESTRUCTIVE classifications.
