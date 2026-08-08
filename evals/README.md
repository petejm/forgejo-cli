# Evals

Seven cases covering auth pattern selection, request construction, pagination,
and the destructive-operation guardrails.

## Layout

Each case is a directory. The runner discovers cases by globbing
`evals/**/prompt.md` alongside `graders/*.md`:

```
evals/
  <case-id>/
    prompt.md          — the user turn the case replays
    graders/*.md       — plain-English assertions, scored per file
```

`prompt.md` holds only the prompt text. Each file under `graders/` is one scored
grader; assertions inside it are written so they can be judged from the
transcript alone.

## Cases

| Case | Covers |
|------|--------|
| `create-private-repo` | happy path, `/user/repos`, status checked before parse |
| `list-open-issues` | `state`/`type` filters, pagination accumulates results |
| `delete-repo-confirm` | DELETE stops for confirmation, request shown redacted |
| `admin-create-user` | admin POST stops for confirmation, generated password |
| `merge-pr-confirm` | irreversible merge stops for confirmation, `Do` strategy |
| `create-api-token` | basic auth actually reaches the server, credentials resolved |
| `admin-list-users` | admin GET does *not* confirm, pagination |

## Running

The runner is `claude plugin eval`, targeting either this directory or the
plugin by name. It is gated behind early access — on an account without it the
command exits 1 with `plugin eval is currently in early access`, and the cases
below have not been executed here. Until that gate opens, treat them as a
written specification: the assertions are the contract the skill is expected to
satisfy, and they are worth reading before changing auth or pagination behavior.

## Writing a new case

Keep assertions phrased against **observable outcomes**, not against a
particular implementation. `an Authorization header is actually sent` survives a
refactor from `--netrc-file` to `-u`; `the command contains --netrc-file` does
not, and would go green on a request that authenticates with nothing at all.
