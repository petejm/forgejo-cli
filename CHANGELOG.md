# Changelog

All notable changes to forgejo-cli are documented here.

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
- Canonical curl pattern sync note in CLAUDE.md contributing guidelines
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
- **Body parsing bug**: replaced `echo "$response"` and `echo "$body"` with `printf '%s\n'` across all canonical curl patterns; `echo` strips trailing newlines causing incorrect status code extraction on single-line JSON responses
- **Pagination infinite loop**: added 100-page ceiling to the pagination while loop
- **Error path handling**: replaced `return` with `exit 1` in auth-patterns.md error handlers
- **Admin operation grouping**: split `list users` (read-only GET) from `create user` (destructive POST); read operations no longer trigger confirmation prompts

### Security
- Added `eval "$TOKEN_CMD"` security warning: compromised `.local.md` files enable arbitrary code execution at the Claude Code process privilege level

### Added
- No-arg `/forgejo` command now displays usage summary with available operations and examples
- `CLAUDE.md` with project structure, contributing guidelines, and the `printf` rule
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
- Added pagination support with `Link` header parsing
- Added Bearer token format validation
- Fixed Swagger field name references for accurate endpoint discovery
- Added credential newline validation
- Sanitized all examples to remove instance-specific references
- Rewrote README for public release
