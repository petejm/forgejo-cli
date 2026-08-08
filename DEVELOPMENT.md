# forgejo-cli

A Claude Code plugin that teaches Claude to interact with any Forgejo or Gitea instance via the REST API.

## File Structure

```
.claude-plugin/
  plugin.json          — plugin manifest (name, version, keywords, license)
  marketplace.json     — marketplace catalog so the plugin is installable via /plugin
commands/
  forgejo.md           — /forgejo slash command definition
skills/
  forgejo-api/
    SKILL.md           — main skill: auth flow, API call pattern, pagination, gotchas, discovery
    references/
      auth-patterns.md — complete auth examples for all 3 methods (token-cmd, op, env)
      endpoints.md     — 20 supported operations with exact curl snippets
evals/
  README.md            — case inventory, layout, and how to write a new case
  <case-id>/
    prompt.md          — the user turn the case replays
    graders/*.md       — plain-English assertions, scored per file
tests/
  lint.sh              — runs every check, tallies pass/fail, exits non-zero on any failure
  self-test.sh         — breaks one thing per case and proves each check goes red
  checks/              — the checks themselves: manifests, frontmatter, evals, crossrefs,
                         counts, shellfences, safety
.github/
  workflows/
    ci.yml             — runs lint.sh and self-test.sh on ubuntu-latest and macos-latest
LICENSE                — MIT license text
README.md              — user-facing documentation
CHANGELOG.md           — release history
DEVELOPMENT.md         — this file
```

## How to Test

Run the lint suite from the repo root. It is fully static — it reads files, opens no sockets, and reads no credential, so it is safe to run anywhere:

```bash
bash tests/lint.sh
bash tests/self-test.sh
```

`tests/lint.sh` runs all seven checks and exits non-zero if any fails. `tests/self-test.sh` is the meta-test: it copies the repo to a temp directory, breaks exactly one asserted thing per case, and requires the matching check to go red — so a check that has quietly stopped inspecting anything cannot pass as green. Both run in CI on `ubuntu-latest` and `macos-latest`; the macOS leg is the real bash 3.2 gate, so invoke `/bin/bash tests/...` rather than relying on `PATH`.

Note the deliberate exemption: `CHANGELOG.md` is skipped by the staleness, prose-count, and endpoint-count checks, because a changelog records names and counts as they were at that release. It is still scanned for leaked private information. The exemption set is the `HISTORICAL` constant in `tests/checks/_common.py` and `tests/lint.sh` prints it on every run.

Then validate both manifests. Pass each path explicitly — given a bare directory, `claude plugin validate` resolves to the marketplace manifest and never checks `plugin.json`:

```bash
claude plugin validate .claude-plugin/plugin.json --strict
claude plugin validate .claude-plugin/marketplace.json --strict
```

`--strict` turns unrecognized-field warnings into errors, which catches a typo'd or leftover manifest key before it ships.

The behavioral cases live in `evals/`, one directory per case, in the layout `claude plugin eval` discovers (`evals/**/prompt.md` alongside `graders/*.md`):

```bash
claude plugin eval .
```

There is no `claude eval` subcommand — earlier revisions of this file said there was. `claude plugin eval` is the real one, and it is gated behind early access; on an account without it the command exits 1. See [evals/README.md](evals/README.md) for the case inventory, the early-access caveat, and how to write a new case.

The cases cover auth pattern selection, request construction, pagination, and the destructive-operation guardrails.

## Releasing

`plugin.json` `version`, the `version` on the `forgejo-cli` entry in `marketplace.json`, and the newest CHANGELOG heading must all carry the same string. `claude plugin tag` creates the `{name}--v{version}` git tag and validates that the manifest and the enclosing marketplace entry agree, so run it rather than tagging by hand.

## Contributing

- Keep **gotchas accurate** — every entry in Section 6 of SKILL.md reflects a real failure mode. Only add a gotcha if it's been observed in practice.
- **Test auth patterns** before updating them — especially the `eval "$TOKEN_CMD"` and `--netrc-file <(printf ...)` patterns. These are subtle and easy to break. The netrc values must stay quoted and `$HOST` must stay port-stripped; `tests/checks/shellfences.py` enforces both.
- **Never use `echo "$response"`** to split curl output — use `printf '%s\n' "$response"`. POSIX says of `echo`: "If the first operand consists of a `'-'` followed by one or more characters from the set {`'e'`, `'E'`, `'n'`}, or if any of the operands contain a `<backslash>` character, the results are implementation-defined." API responses contain both. `printf '%s\n'` is specified. (This rule was previously justified by claiming `echo` strips trailing newlines. It does not — POSIX: "The echo utility writes its arguments to standard output, followed by a `<newline>`." The stripping is done by `$( )` command substitution, before `echo` ever runs.)
- **Destructive operations** (DELETE, merge, admin POST) must always require explicit user confirmation. Do not relax this guardrail.
- Keep `references/endpoints.md` in sync with `SKILL.md` Section 4 — both list the 20 supported operations and their DESTRUCTIVE classifications.
- Keep the **canonical curl pattern** in sync between `SKILL.md` Section 3 and `references/auth-patterns.md` Section 6 — both define the response parsing and error handling template.
