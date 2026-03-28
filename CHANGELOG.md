# Changelog

All notable changes to forgejo-cli are documented here.

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
