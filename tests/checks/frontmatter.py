"""YAML frontmatter checks for skills and commands.

PyYAML is not guaranteed on a bare GitHub runner, so this parses with PyYAML
when it is importable and falls back to a deliberately strict subset parser
(top-level `key:` scalars plus `|`/`>` block scalars) otherwise. The fallback is
stricter than YAML, never looser -- it can reject a valid-but-exotic document,
it cannot accept a malformed one. Which parser ran is printed, so a green run
never hides the fact that the weaker parser was used.
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import Result, list_files, read, repo_root  # noqa: E402

try:
    import yaml  # type: ignore

    HAVE_YAML = True
except ImportError:
    HAVE_YAML = False

KEY = re.compile(r"^([A-Za-z0-9_-]+):(?: +(.*))?$")


def parse_minimal(text):
    """Parse the top-level key set of a simple YAML mapping. Raises ValueError."""
    data = {}
    lines = text.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip() or line.lstrip().startswith("#"):
            i += 1
            continue
        if line[:1] in (" ", "\t"):
            raise ValueError("line %d: unexpected indentation outside a block scalar" % (i + 1))
        m = KEY.match(line)
        if not m:
            raise ValueError("line %d: not a top-level 'key: value' mapping entry: %r" % (i + 1, line))
        key, value = m.group(1), (m.group(2) or "")
        if value.strip() in ("|", ">", "|-", ">-", "|+", ">+"):
            block = []
            i += 1
            while i < len(lines) and (not lines[i].strip() or lines[i][:1] in (" ", "\t")):
                block.append(lines[i].strip())
                i += 1
            data[key] = " ".join(x for x in block if x)
            continue
        data[key] = value.strip().strip("\"'")
        i += 1
    return data


def split_frontmatter(res, rel, text):
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return None
    for n in range(1, len(lines)):
        if lines[n].strip() == "---":
            return "\n".join(lines[1:n])
    res.fail(rel, "frontmatter opens with '---' but is never closed")
    return False


def main():
    root = repo_root()
    res = Result("frontmatter")
    res.note("parser: %s" % ("PyYAML" if HAVE_YAML else "minimal fallback (PyYAML unavailable)"))

    required = ["skills/forgejo-api/SKILL.md", "commands/forgejo.md"]
    all_md = [f for f in list_files(root) if f.endswith(".md")]

    for rel in required:
        if not os.path.exists(os.path.join(root, rel)):
            res.fail(rel, "required file is missing")

    checked = 0
    for rel in all_md:
        text = read(root, rel)
        raw = split_frontmatter(res, rel, text)
        if raw is None:
            if rel in required:
                res.fail(rel, "has no YAML frontmatter (required)")
            continue
        if raw is False:
            continue
        checked += 1
        if HAVE_YAML:
            try:
                data = yaml.safe_load(raw)
            except Exception as exc:
                res.fail(rel, "frontmatter is not valid YAML: %s" % exc)
                continue
            if not isinstance(data, dict):
                res.fail(rel, "frontmatter is not a mapping (got %s)" % type(data).__name__)
                continue
        else:
            try:
                data = parse_minimal(raw)
            except ValueError as exc:
                res.fail(rel, "frontmatter rejected by fallback parser: %s" % exc)
                continue

        if rel.endswith("SKILL.md"):
            expected = os.path.basename(os.path.dirname(rel))
            if data.get("name") != expected:
                res.fail(
                    rel,
                    "frontmatter name %r != parent directory %r (Claude Code resolves "
                    "the skill by directory name)" % (data.get("name"), expected),
                )
            if not str(data.get("description", "")).strip():
                res.fail(rel, "frontmatter 'description' is empty (skill will not trigger)")
        if rel.startswith("commands/"):
            if not str(data.get("description", "")).strip():
                res.fail(rel, "command frontmatter 'description' is empty")

    if checked == 0:
        res.fail("frontmatter", "no frontmatter documents found -- the check had nothing to verify")

    return res.finish()


if __name__ == "__main__":
    sys.exit(main())
