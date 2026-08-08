#!/usr/bin/env bash
# forgejo-cli lint suite.
#
# Runs entirely offline. It never contacts a Forgejo instance, never reads a
# credential, and never opens a network socket. Everything it asserts is
# derived from files in this repository.
#
# Usage:
#   /bin/bash tests/lint.sh            # run everything
#   /bin/bash tests/lint.sh --only counts
#   /bin/bash tests/lint.sh --list
#
# Invoke it as `/bin/bash tests/lint.sh`, not `./tests/lint.sh`: the target is
# bash 3.2 (the /bin/bash macOS still ships), and a shebang re-resolves PATH,
# which on a developer machine frequently finds a Homebrew bash 5 instead.
#
# bash 3.2 constraints observed throughout: no associative arrays, no mapfile,
# no ${var,,}, no `wait -n`, no negative `head -n`, no `grep -P`.
#
# `set -o pipefail` is deliberately NOT set, and no pipeline in this file ends
# in `grep -q`: under pipefail the producer takes SIGPIPE when grep exits early
# on a match, so the pipeline reports failure precisely because the match
# succeeded. Where a match must be tested, the output is captured first.

set -u

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$SCRIPT_DIR/.." && pwd)
CHECKS_DIR="$SCRIPT_DIR/checks"

CHECK_NAMES="manifests frontmatter evals crossrefs counts shellfences safety"

ONLY=""
while [ $# -gt 0 ]; do
  case "$1" in
    --only)
      ONLY="${2:-}"
      shift 2
      ;;
    --list)
      for name in $CHECK_NAMES; do echo "$name"; done
      exit 0
      ;;
    -h|--help)
      sed -n '2,20p' "$0"
      exit 0
      ;;
    *)
      echo "unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

# Do not litter the tree with __pycache__: it is untracked, unignored, and would
# otherwise be picked up by the public-safety scan's own file inventory.
export PYTHONDONTWRITEBYTECODE=1

if ! command -v python3 >/dev/null 2>&1; then
  echo "FATAL: python3 is required and was not found on PATH" >&2
  exit 2
fi

PASSED=0
FAILED=0
FAILED_NAMES=""

echo "forgejo-cli lint"
echo "  repo:   $ROOT"
echo "  bash:   ${BASH_VERSION:-unknown}"
py_version=$(python3 --version 2>&1)
echo "  python: $py_version"
echo

for name in $CHECK_NAMES; do
  if [ -n "$ONLY" ] && [ "$ONLY" != "$name" ]; then
    continue
  fi
  script="$CHECKS_DIR/$name.py"
  if [ ! -f "$script" ]; then
    echo "  FATAL: check script missing: $script" >&2
    FAILED=$((FAILED + 1))
    FAILED_NAMES="$FAILED_NAMES $name"
    continue
  fi
  echo "==> $name"
  if python3 "$script" "$ROOT"; then
    echo "    ok"
    PASSED=$((PASSED + 1))
  else
    status=$?
    if [ "$status" -gt 1 ]; then
      echo "    ERROR: check crashed (exit $status)"
    fi
    FAILED=$((FAILED + 1))
    FAILED_NAMES="$FAILED_NAMES $name"
  fi
  echo
done

# ---------------------------------------------------------------------------
# Advisory steps. These never change the exit status: shellcheck and the
# `claude` CLI are not present on every runner, and a check that is sometimes
# absent must not be allowed to sometimes pass silently as if it had run.
# ---------------------------------------------------------------------------
if [ -z "$ONLY" ]; then
  echo "==> advisory"
  if command -v shellcheck >/dev/null 2>&1; then
    sc_out=$(shellcheck --severity=warning "$SCRIPT_DIR/lint.sh" 2>&1)
    if [ -n "$sc_out" ]; then
      echo "    shellcheck (advisory, non-blocking):"
      echo "$sc_out" | sed 's/^/      /'
    else
      echo "    shellcheck: clean"
    fi
  else
    echo "    shellcheck: not installed, skipped"
  fi

  if command -v claude >/dev/null 2>&1; then
    cv_out=$(cd "$ROOT" && claude plugin validate . 2>&1)
    cv_status=$?
    if [ "$cv_status" -eq 0 ]; then
      echo "    claude plugin validate: ok"
    else
      echo "    claude plugin validate (advisory, non-blocking): exit $cv_status"
      echo "$cv_out" | sed 's/^/      /'
    fi
  else
    echo "    claude plugin validate: CLI not installed, skipped"
  fi
  echo
fi

echo "---------------------------------------------"
echo "passed: $PASSED   failed: $FAILED"
if [ "$FAILED" -gt 0 ]; then
  echo "failing checks:$FAILED_NAMES"
  exit 1
fi
echo "all checks passed"
exit 0
