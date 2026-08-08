# Changelog

All notable changes to forgejo-cli are documented here.

## v1.2.0 — 2026-08-08

### Added
- `LICENSE` with the full MIT text. `plugin.json` and the README both declared MIT, but with no license file a public repo is all-rights-reserved by default and the declared SPDX identifier grants nothing.
- `.claude-plugin/marketplace.json`, so the plugin can be installed persistently with `/plugin marketplace add petejm/forgejo-cli` + `/plugin install forgejo-cli@petejm-plugins`. The only previously documented install path was `claude --plugin-dir`, which lasts for the duration of one session.
- `repository` and `$schema` fields in `plugin.json`
- `tests/checks/`: static repo lint checks that read files only and never contact a Forgejo instance
- `tests/lint.sh` and `tests/self-test.sh`, plus `.github/workflows/ci.yml` running both on `ubuntu-latest` and `macos-latest`. The repo previously had no tests and no CI. `self-test.sh` is a meta-test: it copies the repo to a temp directory, breaks one asserted thing per case, and requires the matching check to go red — 23 cases, so a check that has quietly stopped inspecting anything cannot pass as green.
- Releasing section in DEVELOPMENT.md: `plugin.json`, the marketplace entry, and the newest CHANGELOG heading must carry the same version string, and `claude plugin tag` enforces that.
- Token hygiene guidance in `endpoints.md`: narrowest scopes, the repo-scoped-token restriction, revocation via `DELETE /api/v1/users/{username}/tokens/{token}`, and the create-verify-delete rotation order.
- A "Beyond the 20" table in `endpoints.md` (with a pointer from SKILL.md Section 4) covering six operations present in both the Forgejo and Gitea specs but outside the supported set: `POST /orgs/{org}/repos`, `GET issues/{index}`, `GET pulls/{index}`, `GET issues/{index}/comments`, `GET|PUT contents/{filepath}`, `DELETE tokens/{token}`. The supported count stays at 20.
- `auth-patterns.md` Section 9 on OAuth2: `Bearer` for OAuth2 access tokens, `token` for personal access tokens, and an explicit rejection of the query-string form, which leaks the credential into access logs.

### Fixed
- **False security claim in README**: "Token auth — uses `Authorization: token` header, no command-line exposure via `-u`" read as a promise that the token stays off the command line. It does not: the `-H` value sits in `curl`'s argv and is visible to `ps` and `/proc/<pid>/cmdline` exactly as `-u` is. Replaced with the actual exposure plus the `-H @<(...)` mitigation.
- **Over-claimed process substitution**: "credentials exist only as a file descriptor, never on disk" held only where `/dev/fd` exists. `man bash`: "Process substitution is supported on systems that support named pipes (FIFOs) or the /dev/fd method of naming open files." Scoped the claim to Linux and macOS in both the Security list and How It Works.
- **Nonexistent test command**: DEVELOPMENT.md instructed contributors to run `claude eval evals/evals.json`. There is no `claude eval` subcommand. The real one is `claude plugin eval`, which discovers `evals/**/case.yaml` or `evals/**/prompt.md` + `graders/*.md` — a layout `evals.json` did not match. DEVELOPMENT.md now documents `claude plugin eval .` against the ported cases, plus the `claude plugin validate --strict` invocations that check both manifests.
- **Stale "291-endpoint" count in README**: v1.1.1 claimed this was replaced repo-wide, but the replacement landed only in the intro line and the count survived under Supported Operations. Removed rather than updated — the true figure varies by Forgejo version and instance config.
- **Destructive-gate scope drift in README**: v1.1.1 expanded the confirmation gate to cover merges in SKILL.md; the README still described it as DELETE and admin only, in two places.
- **Missing timeouts in README's Swagger example**: the Security list promises every `curl` call carries `--connect-timeout 10 --max-time 30`; the discovery example had neither, so an unreachable instance hung with no ceiling.
- **False rationale for the `printf` rule** (CHANGELOG v1.1.0 and DEVELOPMENT.md): `echo` does not strip trailing newlines. POSIX: "The echo utility writes its arguments to standard output, followed by a `<newline>`." The stripping is done by `$( )` command substitution, before `echo` runs. The convention stands on the real reason — POSIX makes `echo`'s output implementation-defined for operands containing a backslash or a leading `-n`/`-e`/`-E`.
- **v1.0.0 credited `Link` header pagination that never shipped**: annotated in place; the implementation has always been `page`/`limit` query parameters with an array-length termination check.
- **Stale `CLAUDE.md` references**: the file was renamed to `DEVELOPMENT.md` after v1.1.1 shipped; two v1.1.x entries still named the old path, and the rename itself had no entry.
- **netrc `machine` name kept the port**, so basic auth silently sent nothing. `curl` matches the netrc `machine` token against the bare host, so `machine host:3000` never matches a request to `host:3000` — and the failure surfaces as a 401, not as a config error. Reproduced against a local listener: with the port, the server logged no `Authorization` header at all; without it, `Basic …`. `$HOST` derivation now strips scheme, userinfo, port and path, and gotcha #3 documents the "401 with no `Authorization:` line" signature so the next reader does not go debugging password escaping.
- **netrc values were unquoted, truncating any password containing a space.** netrc is whitespace-tokenized and has no escaping in the unquoted form, so `password pw with space` was silently read as `pw` (reproduced: the server decoded `alice:pw`). Entries are now emitted quoted through a `netrc_esc` helper that escapes `\` and `"`, with the curl 7.84.0 version floor documented and a fallback for older curl.
- **Pagination loop could crash or stop early.** It appended API responses to a jq array without normalizing the `{"data":[...]}` envelope against a bare array — `jq -n '$a + $b'` exits 5 with "array and object cannot be added" — and it terminated on a hardcoded `-lt 50`, which drops results on any instance whose `MAX_RESPONSE_ITEMS` differs from the default (against a mock advertising 25 with 57 items, the old loop collected 25). The loop now normalizes both response shapes, checks jq's exit status, terminates on the `Link` header's `rel="next"`, and reads the real page size from `/api/v1/settings/api`.
- **Wrong list-issues query parameters**: `milestone` and `assignee` do not exist; the spec's `issueListIssues` parameters are `milestones` and `assigned_by`. Unknown parameters are ignored, so a typo returned HTTP 200 with an unfiltered list — a silent wrong answer rather than an error. Also documented `q`, `created_by`, `mentioned_by`, `since`, `before` and `sort`.
- **Swagger discovery snippets used a `/api/v1` key prefix that does not exist.** That prefix is the spec's top-level `basePath`; 0 of 327 Forgejo path keys and 0 of 308 Gitea path keys carry it, so `spec['paths']['/api/v1/…']` always raised `KeyError`. Keyword listing also printed the bare path, which 404s when concatenated onto `$FORGEJO_URL`; it now prints `basePath` + path.
- **`$USER` used where the Forgejo username was meant.** Every login shell exports `USER`, so it never trips an unset guard — it silently authenticates as the operator's OS account. Credential variables are now `OP_USER`/`OP_PASS` throughout, with `: "${OP_USER:?}"` guards.
- **Merge PR body was wrong in three ways**: the `Do` enum has six values (`merge`, `rebase`, `rebase-merge`, `squash`, `fast-forward-only`, `manually-merged`), not four; the endpoint returns HTTP 200 with an empty body, so parsing the response as JSON fails on success; and Forgejo uses capitalized field names where Gitea ≥1.27 uses snake_case.
- **Org `visibility` enum was incomplete** — `CreateOrgOption.visibility` is `public|limited|private`.
- **2FA guidance was over-scoped**: the OTP header pairs with basic auth only, not with token auth, and the header name is instance-flavored (`X-FORGEJO-OTP` vs `X-GITEA-OTP`) — read it from `securityDefinitions.TOTPHeader.name` rather than hardcoding either.
- **Config frontmatter parsing was unbounded**, so body content below the frontmatter could be picked up as a config value — including as `token_cmd`, which is `eval`'d. Extraction is now bounded to the frontmatter block, strips inline comments, and trims trailing whitespace.
- **Trace suppression restored `set -x` before the credential was expanded**, and the `&&` form silently exited 1 when it landed as a script's last statement. Replaced with a single trace-off subshell wrapping resolve-and-use.
- **Missing timeouts and unchecked HTTP status** at five skill sites; both Swagger fetches now require a 200 before parsing and fail with a named error instead of a `json.load` traceback. `000` (connection failure) is handled explicitly in both canonical patterns and appears in both error-classification tables.
- **The create-token response was echoed.** The `sha1` is returned exactly once and is not recoverable afterwards; echoing it writes the token into the session transcript. Replaced with a guarded extraction piped to a store command.
- **README and DEVELOPMENT.md documented `--netrc-file <(echo ...)`** after the skill moved to the quoted `printf` form — re-teaching the exact whitespace-truncation bug fixed above.
- **README's `token_cmd` example used `op item get --fields password`**, the bare-name form the skill's own gotcha #2 warns about; and its "use field IDs, not labels" note contradicted the skill's `--fields "label=…"` guidance. Both now match the skill, which points at `op read` for single-field lookups per 1Password's own reference.
- **README described tokens as using a `Bearer` header** in How It Works while the Security section and the skill both specify `Authorization: token`. Gitea documents only the `token` prefix for personal access tokens, so `token` is the portable choice.
- **`commands/forgejo.md` conditioned on `$ARGUMENTS`**, a token that is substituted away before the model reads it, so the emptiness test could never be true. It now tests the literal `ARGUMENTS:` line.

### Changed
- Eval cases moved from a single `evals/evals.json` to one directory per case (`evals/<case-id>/prompt.md` plus `graders/*.md`) — the layout `claude plugin eval` actually discovers. See `evals/README.md`. The `create-api-token` case was rewritten to assert that credentials are actually *sent* — a `machine` entry with no port, a space-containing password surviving intact — rather than merely written, so it catches the silent no-`Authorization`-header failure.
- `commands/forgejo.md` now marks `repo delete` and `pr merge` `(DESTRUCTIVE)` alongside `admin create user`, matching the guardrail the skill and the eval cases enforce, and explains the marker once below the list.

## v1.1.1 — 2026-03-28

### Fixed (R1-R3 tabula rasa)
- **PR merge missing from destructive gate**: merge PR is irreversible but was not covered by Section 8's confirmation requirement (scoped to DELETE and admin ops only); expanded scope to include merge operations
- **Swagger keyword divergence**: SKILL.md and endpoints.md still used `'release'` as default keyword after CHANGELOG v1.1.0 claimed it was fixed to `'webhook'`; aligned all three files
- **204 body guard missing from auth-patterns.md**: canonical curl pattern in auth-patterns.md omitted `[[ "$http_code" == "204" ]] && body=""` present in SKILL.md; DELETE ops would hit parse failures
- **`set +x` never restored**: trace state now saved and restored around credential resolution in both token-cmd and op auth paths
- **`--reveal` omitted from SKILL.md op auth**: Section 2 quick pattern lacked `--reveal` flag; concealed 1Password fields would return `[concealed]` literal
- **`$USER` shell variable collision**: token creation endpoints used `$USER` (OS username) instead of `$FORGEJO_USER`; silent wrong-endpoint bug if OS and Forgejo usernames differ
- **`token_cmd` quote stripping**: only stripped double quotes; single-quoted values (common for shell commands) passed literal `'` chars to `eval`
- **Error check block missing from auth-patterns.md**: canonical pattern in Section 6 stopped after body parsing with no status code check
- **Link header documentation contradiction**: Gotcha #8 claimed "uses Link header" but no Link parsing code exists; aligned with actual array-length implementation
- **Plugin version stale**: plugin.json was `1.0.0` after v1.1.0 changes shipped; bumped to match CHANGELOG
- **Mixed bracket styles**: standardized POSIX `[ ... ]` to bash `[[ ... ]]` in canonical pattern

### Security
- Added `eval "$TOKEN_CMD"` security warning to user-facing README (was only in auth-patterns.md)
- Added input validation note: user-provided values (repo names, usernames) must be validated before shell interpolation
- Added `FORGEJO_URL` trust boundary awareness via frontmatter-only parsing warning

### Added
- 4 new eval cases: `admin-create-user`, `merge-pr-confirm`, `create-api-token`, `admin-list-users` (7 total, up from 3)
- `type=issues` assertion added to `list-open-issues` eval
- `python3` added to README requirements (used in error parsing and Swagger discovery)
- Canonical curl pattern sync note in `CLAUDE.md` (renamed to `DEVELOPMENT.md` after this release) contributing guidelines
- `tokens` and `admin` keywords in plugin.json

### Changed
- Command help categories use singular forms (`repo`, `issue`, `pr`) matching example syntax
- Admin help text now includes "list users" alongside "create user"
- Hardcoded "291-endpoint" count in README replaced with version-independent "your instance's full API surface"
- Placeholder names standardized to `my-forgejo` across all config examples
- Gotcha #7 (`--exit-code`) now includes context note about Forgejo setup scripts
- `.gitignore` description in README clarified (protects repo directory, not `~/.claude/`)

## v1.1.0 — 2026-03-28

### Fixed
- **Body parsing bug**: replaced `echo "$response"` and `echo "$body"` with `printf '%s\n'` across all canonical curl patterns (the mechanism originally cited in this entry — that `echo` strips trailing newlines — was wrong; corrected in v1.2.0)
- **Pagination infinite loop**: added 100-page ceiling to the pagination while loop
- **Error path handling**: replaced `return` with `exit 1` in auth-patterns.md error handlers
- **Admin operation grouping**: split `list users` (read-only GET) from `create user` (destructive POST); read operations no longer trigger confirmation prompts

### Security
- Added `eval "$TOKEN_CMD"` security warning: compromised `.local.md` files enable arbitrary code execution at the Claude Code process privilege level

### Added
- No-arg `/forgejo` command now displays usage summary with available operations and examples
- `CLAUDE.md` (renamed to `DEVELOPMENT.md` after v1.1.1) with project structure, contributing guidelines, and the `printf` rule
- `license` and `homepage` fields in plugin.json

### Changed
- README swagger discovery example: fixed keyword default from `'release'` to `'webhook'` to match invocation example

## v1.0.0 — 2026-03-14

### Added
- Initial public release
- 20 built-in operations: repos (6), issues (4), PRs (3), users/orgs (3), admin (2), tokens (2)
- 3 auth methods: `token-cmd` (recommended), `op` (1Password), `env` (environment variable)
- Swagger-based discovery for the full Forgejo API surface
- 10 gotchas from real debugging sessions encoded as hard rules
- Process substitution credential handling (keeps secrets off disk)
- Destructive operation guardrails with confirmation gates

### Fixed (R1-R3 tabula rasa)
- Added `--connect-timeout` and `--max-time` to all curl calls
- Added pagination support via `page`/`limit` query parameters with an array-length termination check (this entry originally read "with `Link` header parsing"; no `Link` parsing was ever implemented — corrected in v1.2.0)
- Added Bearer token format validation
- Fixed Swagger field name references for accurate endpoint discovery
- Added credential newline validation
- Sanitized all examples to remove instance-specific references
- Rewrote README for public release
