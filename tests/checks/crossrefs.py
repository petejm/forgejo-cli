"""Internal cross-reference checks.

Three things go stale silently in a docs-only repo: a path that names a file
that has been renamed or deleted, a "Section N" pointer that outlives the
section, and the old name of a renamed file. All three are cheap to verify and
none of them are visible to a human reviewer reading one file at a time.

Scope note: only inline backticked paths and markdown links are inspected.
Fenced code blocks are deliberately skipped -- a path inside a shell example is
frequently a runtime path (`~/.claude/...`, `${FORGEJO_URL}/...`) that has no
business resolving against the repo.
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import HISTORICAL, Result, list_files, markdown_files, read, repo_root  # noqa: E402

PATH_TOKEN = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_./-]*\.(md|json|sh|yml|yaml)$")
INLINE_CODE = re.compile(r"`([^`\n]+)`")
MD_LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
SECTION_A = re.compile(r"`?([A-Za-z0-9_./-]+\.md)`? +Section +(\d+)")
SECTION_B = re.compile(r"Section +(\d+) +of +`?([A-Za-z0-9_./-]+\.md)`?")
SECTION_HEADING = re.compile(r"^## +Section +(\d+):")

# `.local.md` is the user's own config file. It is gitignored by design and
# must never exist in the repo, so it can never resolve.
PATH_EXEMPT = (".local.md",)

# The file was renamed CLAUDE.md -> DEVELOPMENT.md. Any live doc still saying
# CLAUDE.md points readers at a file that is not there.
OLD_NAME = "CLAUDE" + ".md"


def strip_fences(text):
    """Blank out fenced-code bodies, preserving line numbering."""
    out = []
    inside = False
    for line in text.split("\n"):
        if line.strip().startswith("```"):
            inside = not inside
            out.append("")
            continue
        out.append("" if inside else line)
    return out


def resolves(mention, tracked):
    if mention in tracked:
        return True
    suffix = "/" + mention
    for t in tracked:
        if t.endswith(suffix):
            return True
    return False


def main():
    root = repo_root()
    res = Result("crossrefs")
    tracked = set(list_files(root))
    docs = markdown_files(root)
    if not docs:
        res.fail("crossrefs", "no markdown files found -- the check had nothing to verify")
        return res.finish()

    section_index = {}

    def sections_of(rel):
        if rel not in section_index:
            found = set()
            for line in read(root, rel).split("\n"):
                m = SECTION_HEADING.match(line)
                if m:
                    found.add(m.group(1))
            section_index[rel] = found
        return section_index[rel]

    def locate(mention):
        if mention in tracked:
            return mention
        suffix = "/" + mention
        for t in sorted(tracked):
            if t.endswith(suffix):
                return t
        return None

    path_mentions = 0
    for rel in docs:
        lines = strip_fences(read(root, rel))
        historical = os.path.basename(rel) in HISTORICAL

        for n, line in enumerate(lines, 1):
            candidates = []
            for m in INLINE_CODE.finditer(line):
                candidates.append(m.group(1).strip())
            for m in MD_LINK.finditer(line):
                target = m.group(1).strip()
                if target.startswith(("http://", "https://", "mailto:", "#")):
                    continue
                candidates.append(target.split("#", 1)[0])

            for cand in candidates:
                if any(x in cand for x in PATH_EXEMPT):
                    continue
                if not PATH_TOKEN.match(cand):
                    continue
                path_mentions += 1
                if historical:
                    continue
                if not resolves(cand, tracked):
                    res.fail("%s:%d" % (rel, n), "references %r, which does not exist in the tree" % cand)

            if historical:
                continue

            for m in SECTION_A.finditer(line):
                target, num = m.group(1), m.group(2)
                real = locate(target)
                if real is None:
                    res.fail("%s:%d" % (rel, n), "Section pointer names %r, which does not exist" % target)
                elif num not in sections_of(real):
                    res.fail(
                        "%s:%d" % (rel, n),
                        "points at '%s Section %s' but that file has no '## Section %s:' heading"
                        % (target, num, num),
                    )
            for m in SECTION_B.finditer(line):
                num, target = m.group(1), m.group(2)
                real = locate(target)
                if real is None:
                    res.fail("%s:%d" % (rel, n), "Section pointer names %r, which does not exist" % target)
                elif num not in sections_of(real):
                    res.fail(
                        "%s:%d" % (rel, n),
                        "points at 'Section %s of %s' but that file has no '## Section %s:' heading"
                        % (num, target, num),
                    )

    if path_mentions == 0:
        res.fail("crossrefs", "no internal path references found at all -- extraction is probably broken")

    # --- renamed-file staleness --------------------------------------------
    live_hits = 0
    for rel in markdown_files(root, include_historical=False):
        for n, line in enumerate(read(root, rel).split("\n"), 1):
            if OLD_NAME in line:
                live_hits += 1
                res.fail(
                    "%s:%d" % (rel, n),
                    "names %s, which was renamed to DEVELOPMENT.md" % OLD_NAME,
                )
    if live_hits == 0:
        res.note(
            "no live doc names the pre-rename filename (%s files exempt as historical record)"
            % ", ".join(HISTORICAL)
        )

    return res.finish()


if __name__ == "__main__":
    sys.exit(main())
