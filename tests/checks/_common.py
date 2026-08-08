"""Shared helpers for the forgejo-cli lint checks.

Every check module is a standalone script: `python3 tests/checks/<name>.py <repo-root>`.
It prints findings to stdout and exits 1 if any hard assertion failed, 0 otherwise.
No check may open a network socket, read a credential, or contact a Forgejo instance.
"""

import os
import subprocess
import sys

# Files that record history rather than describe the current tree. A changelog
# entry names things as they were at that release; "fixing" it falsifies the
# record. These are exempt from staleness and current-state checks, and only
# from those -- they are still scanned for public-safety leaks.
HISTORICAL = ("CHANGELOG.md",)

TEXT_SUFFIXES = (
    ".md", ".json", ".yml", ".yaml", ".sh", ".py", ".txt", ".gitignore", "",
)


class Result(object):
    def __init__(self, name):
        self.name = name
        self.failures = []
        self.notes = []

    def fail(self, where, message):
        self.failures.append("%s: %s" % (where, message))

    def note(self, message):
        self.notes.append(message)

    def finish(self):
        for n in self.notes:
            sys.stdout.write("    note: %s\n" % n)
        for f in self.failures:
            sys.stdout.write("    FAIL %s\n" % f)
        return 1 if self.failures else 0


def repo_root():
    if len(sys.argv) > 1:
        return os.path.abspath(sys.argv[1])
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def list_files(root):
    """All files that are part of the working tree, tracked or not, minus ignored.

    Untracked-but-not-ignored files are included on purpose: a leak added in an
    uncommitted file is still a leak, and a lint suite that only sees committed
    files cannot block a bad commit.
    """
    out = []
    try:
        raw = subprocess.check_output(
            ["git", "-C", root, "ls-files", "-c", "-o", "--exclude-standard"],
            stderr=subprocess.DEVNULL,
        )
        names = raw.decode("utf-8", "replace").split("\n")
        for n in names:
            n = n.strip()
            if not n:
                continue
            p = os.path.join(root, n)
            if os.path.isfile(p):
                out.append(n)
    except Exception:
        for dirpath, dirnames, filenames in os.walk(root):
            if ".git" in dirnames:
                dirnames.remove(".git")
            for fn in filenames:
                p = os.path.join(dirpath, fn)
                out.append(os.path.relpath(p, root))
    return sorted(set(out))


def read(root, rel):
    with open(os.path.join(root, rel), "r") as fh:
        return fh.read()


def markdown_files(root, include_historical=True):
    files = [f for f in list_files(root) if f.endswith(".md")]
    if not include_historical:
        files = [f for f in files if os.path.basename(f) not in HISTORICAL]
    return files


def is_texty(rel):
    base = os.path.basename(rel)
    if base.startswith("."):
        return True
    _, ext = os.path.splitext(rel)
    return ext in TEXT_SUFFIXES


def bash_fences(text):
    """Yield (start_line, [lines]) for every ```bash / ```sh fenced block."""
    lines = text.split("\n")
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        if stripped in ("```bash", "```sh", "```shell"):
            start = i + 2  # 1-indexed line of the first body line
            body = []
            i += 1
            while i < len(lines) and lines[i].strip() != "```":
                body.append(lines[i])
                i += 1
            yield start, body
        i += 1


def logical_commands(body_lines, start_line):
    """Join backslash-continued lines into one logical command.

    Returns a list of (line_number, joined_text).
    """
    out = []
    buf = None
    buf_line = 0
    for offset, raw in enumerate(body_lines):
        line = raw.rstrip("\n")
        if buf is None:
            buf = line
            buf_line = start_line + offset
        else:
            buf = buf + " " + line.strip()
        if line.rstrip().endswith("\\"):
            buf = buf.rstrip()[:-1]
            continue
        out.append((buf_line, buf))
        buf = None
    if buf is not None:
        out.append((buf_line, buf))
    return out
