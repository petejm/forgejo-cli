---
description: "Forgejo API operations — repos, issues, PRs, orgs, admin, and raw API calls"
argument-hint: <subcommand> [args...] (e.g., "repo create myrepo --private", "issue list owner/repo", "api GET /repos/owner/repo")
---

If the `ARGUMENTS:` line at the end of this file is empty, display this usage summary and stop:

```
forgejo-cli — Forgejo/Gitea API operations

Usage: /forgejo <operation> [args...]

Available operations:
  repo      — create, list, get, delete (DESTRUCTIVE), search repositories
  issue     — list, create, comment, close/reopen issues
  pr        — list, create, merge (DESTRUCTIVE) pull requests
  user      — get current user, list users (admin)
  org       — create org, list org repos
  admin     — list users, create user (DESTRUCTIVE)
  token     — create and list API tokens
  api       — raw API call: /forgejo api GET /repos/owner/repo
  swagger   — discover endpoints from your instance's Swagger spec

Operations marked DESTRUCTIVE show the exact request and wait for your
explicit confirmation before executing.

Examples:
  /forgejo repo create myrepo --private
  /forgejo issue list owner/repo
  /forgejo pr merge owner/repo 7
  /forgejo api GET /repos/owner/repo
```

Otherwise, invoke the forgejo-cli:forgejo-api skill and follow it exactly as presented to you.

ARGUMENTS: $ARGUMENTS
