---
description: "Forgejo API operations — repos, issues, PRs, orgs, admin, and raw API calls"
argument-hint: <subcommand> [args...] (e.g., "repo create myrepo --private", "issue list owner/repo", "api GET /repos/owner/repo")
---

If $ARGUMENTS is empty, display this usage summary and stop:

```
forgejo-cli — Forgejo/Gitea API operations

Usage: /forgejo <operation> [args...]

Available operations:
  repos     — create, list, get, delete, search repositories
  issues    — list, create, comment, close/reopen issues
  prs       — list, create, merge pull requests
  users     — get current user, list users (admin)
  orgs      — create org, list org repos
  admin     — create user (DESTRUCTIVE — requires confirmation)
  tokens    — create and list API tokens
  api       — raw API call: /forgejo api GET /repos/owner/repo
  swagger   — discover endpoints from your instance's Swagger spec

Examples:
  /forgejo repo create myrepo --private
  /forgejo issue list owner/repo
  /forgejo pr merge owner/repo 7
  /forgejo api GET /repos/owner/repo
```

Otherwise, invoke the forgejo-cli:forgejo-api skill and follow it exactly as presented to you.

ARGUMENTS: $ARGUMENTS
