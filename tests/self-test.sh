#!/usr/bin/env bash
# Meta-test: prove every lint check can actually fail.
#
# A lint check that has quietly stopped matching anything reports the same green
# as a clean tree. That is not hypothetical -- while this suite was being
# written, the netrc matcher was anchored on `<(echo "machine $HOST ...")`, the
# docs were refactored to `<(printf 'machine %s ...' "$HOST" ...)`, and the
# check went on passing while verifying nothing.
#
# Each case copies the repo to a mktemp -d, breaks exactly one asserted thing,
# and requires the corresponding check to go red. The copy is thrown away; the
# real tree is never modified. Every case first asserts the untouched copy is
# green, so a red result is attributable to the mutation and not to the copy.
#
# Usage: /bin/bash tests/self-test.sh
#
# bash 3.2 target; no pipefail, and no pipeline ending in `grep -q`.

set -u

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$SCRIPT_DIR/.." && pwd)

export PYTHONDONTWRITEBYTECODE=1

TOTAL=0
PROVEN=0
BROKEN=""
WORKDIR=$(mktemp -d "${TMPDIR:-/tmp}/forgejo-selftest.XXXXXX")

cleanup() {
  rm -rf "$WORKDIR"
}
trap cleanup EXIT

# Digest of every file's contents, so a mutation that silently matched nothing
# cannot be mistaken for a check that correctly stayed green. This is the same
# failure this whole script exists to catch, one level up.
tree_digest() {
  python3 - "$1" <<'PY'
import hashlib, os, sys
root = sys.argv[1]
h = hashlib.sha256()
for dirpath, dirnames, filenames in os.walk(root):
    if ".git" in dirnames:
        dirnames.remove(".git")
    if "__pycache__" in dirnames:
        dirnames.remove("__pycache__")
    dirnames.sort()
    for fn in sorted(filenames):
        p = os.path.join(dirpath, fn)
        h.update(os.path.relpath(p, root).encode())
        try:
            with open(p, "rb") as fh:
                h.update(fh.read())
        except (IOError, OSError):
            h.update(b"<unreadable>")
print(h.hexdigest())
PY
}

make_copy() {
  dest="$WORKDIR/case-$1"
  rm -rf "$dest"
  mkdir -p "$dest"
  # `.` copies dotfiles too, including .git, so the copy resolves its file list
  # exactly the way the real tree does.
  cp -R "$ROOT"/. "$dest"/ 2>/dev/null
  rm -rf "$dest/tests/checks/__pycache__"
  echo "$dest"
}

# prove <case-name> <check> <expected-substring> <mutation-shell>
prove() {
  name="$1"
  check="$2"
  expect="$3"
  mutation="$4"
  TOTAL=$((TOTAL + 1))

  dest=$(make_copy "$name")

  baseline=$(python3 "$dest/tests/checks/$check.py" "$dest" 2>&1)
  baseline_status=$?
  if [ "$baseline_status" -ne 0 ]; then
    echo "  META-FAIL $name: untouched copy already fails $check (exit $baseline_status)"
    echo "$baseline" | sed 's/^/      /'
    BROKEN="$BROKEN $name"
    return
  fi

  before_digest=$(tree_digest "$dest")
  ( cd "$dest" && eval "$mutation" )
  mutation_status=$?
  if [ "$mutation_status" -ne 0 ]; then
    echo "  META-FAIL $name: mutation command itself failed (exit $mutation_status)"
    BROKEN="$BROKEN $name"
    return
  fi
  after_digest=$(tree_digest "$dest")
  if [ "$before_digest" = "$after_digest" ]; then
    echo "  META-FAIL $name: mutation changed nothing, so a green result proves nothing"
    echo "      (the pattern it edits has probably moved -- fix the mutation, not the check)"
    BROKEN="$BROKEN $name"
    return
  fi

  after=$(python3 "$dest/tests/checks/$check.py" "$dest" 2>&1)
  after_status=$?

  if [ "$after_status" -eq 0 ]; then
    echo "  NOT PROVEN $name: $check still passed after the break"
    BROKEN="$BROKEN $name"
    return
  fi

  # Capture-then-test, never `producer | grep -q`.
  matched=$(printf '%s\n' "$after" | grep -F -- "$expect")
  if [ -z "$matched" ]; then
    echo "  NOT PROVEN $name: $check went red, but not for the expected reason"
    echo "      wanted substring: $expect"
    echo "$after" | sed 's/^/      /'
    BROKEN="$BROKEN $name"
    return
  fi

  echo "  proven  $name -> $check exit $after_status"
  echo "          $(printf '%s\n' "$matched" | head -1 | sed 's/^ *//')"
  PROVEN=$((PROVEN + 1))
}

echo "forgejo-cli lint self-test"
echo "  repo: $ROOT"
echo

# --- public-safety guard ----------------------------------------------------
prove leaked-hostname safety "private git host" \
  'python3 -c "
open(\"README.md\",\"a\").write(\"\nSee \" + \"gond\" + \"olin\" + \".tail\" + \"f4273\" + \".ts\" + \".net\" + \" for details.\n\")
"'

prove leaked-tailnet-ip safety "CGNAT/tailnet address" \
  'python3 -c "
open(\"DEVELOPMENT.md\",\"a\").write(\"\nHost: \" + \".\".join(str(x) for x in (100,106,129,23)) + \"\n\")
"'

prove leaked-home-path safety "real home path" \
  'python3 -c "
open(\"README.md\",\"a\").write(\"\nClone to \" + \"/ho\" + \"me/\" + \"someone/work/forgejo-cli\n\")
"'

# The guard must fail closed when its own matcher stops working.
prove neutered-deny-pattern safety "failed to match their own canary" \
  'python3 -c "
p=\"tests/checks/safety.py\"; s=open(p).read()
target=chr(92)+\"b100\"+chr(92)+\".\"
assert target in s, \"mutation target moved: \" + repr(target)
open(p,\"w\").write(s.replace(target, \"ZZZNEVERMATCHESZZZ\"))
"'

# The guard must fail closed when it has nothing to scan.
TOTAL=$((TOTAL + 1))
empty=$(mktemp -d "$WORKDIR/empty.XXXXXX")
cp "$ROOT/tests/checks/safety.py" "$ROOT/tests/checks/_common.py" "$empty/"
empty_out=$(cd "$empty" && python3 safety.py "$empty" 2>&1)
empty_status=$?
empty_match=$(printf '%s\n' "$empty_out" | grep -F -- "refusing to report a clean tree")
if [ "$empty_status" -ne 0 ] && [ -n "$empty_match" ]; then
  echo "  proven  empty-scan-target -> safety exit $empty_status"
  echo "          $(printf '%s\n' "$empty_match" | head -1 | sed 's/^ *//')"
  PROVEN=$((PROVEN + 1))
else
  echo "  NOT PROVEN empty-scan-target: safety reported clean with nothing to scan (exit $empty_status)"
  BROKEN="$BROKEN empty-scan-target"
fi

# --- version lock -----------------------------------------------------------
prove version-drift manifests "newest CHANGELOG heading" \
  'python3 -c "
import json,io
p=\".claude-plugin/plugin.json\"; d=json.load(open(p)); d[\"version\"]=\"9.9.9\"
open(p,\"w\").write(json.dumps(d,indent=2))
"'

prove marketplace-drift manifests "!= plugin.json version" \
  'python3 -c "
import json
p=\".claude-plugin/marketplace.json\"; d=json.load(open(p))
d[\"plugins\"][0][\"version\"]=\"0.0.1\"
open(p,\"w\").write(json.dumps(d,indent=2))
"'

prove missing-licence manifests "no licence file" \
  'rm -f LICENSE LICENSE.md LICENSE.txt COPYING'

prove malformed-json manifests "not valid JSON" \
  'printf "{ this is not json\n" > .claude-plugin/marketplace.json'

# --- frontmatter ------------------------------------------------------------
prove skill-name-mismatch frontmatter "parent directory" \
  'python3 -c "
p=\"skills/forgejo-api/SKILL.md\"; s=open(p).read()
open(p,\"w\").write(s.replace(\"name: forgejo-api\", \"name: forgejo-apiv2\", 1))
"'

prove unterminated-frontmatter frontmatter "never closed" \
  'python3 -c "
p=\"commands/forgejo.md\"; s=open(p).read().split(chr(10))
del s[s.index(\"---\", 1)]
open(p,\"w\").write(chr(10).join(s))
"'

# --- cross references -------------------------------------------------------
prove stale-renamed-file crossrefs "renamed to DEVELOPMENT.md" \
  'python3 -c "
open(\"DEVELOPMENT.md\",\"a\").write(\"\nSee \" + \"CLAUDE\" + \".md\" + \" for contributing guidelines.\n\")
"'

prove dangling-path-ref crossrefs "does not exist in the tree" \
  'python3 -c "
open(\"README.md\",\"a\").write(\"\nSee the \" + chr(96) + \"references/nonexistent.md\" + chr(96) + \" reference.\n\")
"'

prove dangling-section-ref crossrefs "has no" \
  'python3 -c "
open(\"DEVELOPMENT.md\",\"a\").write(\"\nSee \" + chr(96) + \"SKILL.md\" + chr(96) + \" Section 99 for details.\n\")
"'

# --- operation inventory ----------------------------------------------------
prove dropped-operation counts "is missing operation" \
  'python3 -c "
p=\"skills/forgejo-api/SKILL.md\"; s=open(p).read().split(chr(10))
out=[l for l in s if not l.startswith(\"- \" + chr(96) + \"POST /api/v1/orgs\" + chr(96))]
assert len(out) == len(s)-1, (len(out), len(s))
open(p,\"w\").write(chr(10).join(out))
"'

prove destructive-declassified counts "DESTRUCTIVE in endpoints.md but not in Section 4" \
  'python3 -c "
p=\"skills/forgejo-api/SKILL.md\"; s=open(p).read()
s=s.replace(\"merge PR (DESTRUCTIVE)\", \"merge PR\")
s=s.replace(\"Pull Requests (DESTRUCTIVE\", \"Pull Requests (safe\")
open(p,\"w\").write(s)
"'

prove version-pinned-endpoint-count counts "hardcodes an instance-specific endpoint count" \
  'python3 -c "
open(\"README.md\",\"a\").write(\"\nFor the full 291-endpoint API, see your instance.\n\")
"'

# --- shell examples ---------------------------------------------------------
prove netrc-port-not-stripped shellfences "port produces no Authorization header" \
  'python3 -c "
import re,glob
for p in glob.glob(\"skills/forgejo-api/references/*.md\") + [\"skills/forgejo-api/SKILL.md\"]:
    s=open(p).read()
    s=re.sub(r\"-e .s.\\[/:\\]\\.\\*..\", \"\", s)
    open(p,\"w\").write(s)
"'

prove curl-without-timeout shellfences "can hang forever" \
  'python3 -c "
p=\"skills/forgejo-api/references/endpoints.md\"; s=open(p).read()
open(p,\"w\").write(s.replace(\"--connect-timeout 10 --max-time 30\", \"\", 1))
"'

prove user-variable-collision shellfences "silently authenticates as the wrong account" \
  'python3 -c "
p=\"skills/forgejo-api/references/endpoints.md\"; s=open(p).read()
open(p,\"w\").write(s.replace(chr(34)+chr(36)+\"OP_USER\"+chr(34), chr(34)+chr(36)+\"USER\"+chr(34), 1))
"'

prove netrc-values-unquoted shellfences "is not quoted" \
  'python3 -c "
import glob
for p in glob.glob(\"skills/forgejo-api/references/*.md\") + [\"skills/forgejo-api/SKILL.md\"]:
    s=open(p).read()
    open(p,\"w\").write(s.replace(chr(92)+chr(34)+\"%s\"+chr(92)+chr(34), \"%s\").replace(chr(34)+\"%s\"+chr(34), \"%s\"))
"'

# --- evals ------------------------------------------------------------------
prove empty-grader evals "grader file is empty" \
  'find evals -name "*.md" -path "*/graders/*" | head -1 | xargs -I{} sh -c ": > {}"'

prove eval-without-graders evals "nothing would be scored" \
  'rm -rf evals/merge-pr-confirm/graders'

echo
echo "---------------------------------------------"
echo "assertions proven able to fail: $PROVEN / $TOTAL"
if [ -n "$BROKEN" ]; then
  echo "NOT PROVEN:$BROKEN"
  exit 1
fi
echo "every check was shown to go red when its subject was broken"
exit 0
