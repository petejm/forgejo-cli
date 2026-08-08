"""Public-repo safety scan.

This repository is public. A private hostname, a tailnet address, a device name
or a real home path committed here is not recoverable by deleting it later --
it is in the history and in every clone. This scan is the guard that keeps the
tree clean, so it is written to fail closed in three specific ways:

  * if the file list is empty or implausibly small, it FAILS rather than
    reporting clean -- a guard with nothing to scan has not verified anything;
  * a canary self-test runs every pattern against a synthetic string that is
    known to contain each denied form, and against a benign string. If any
    pattern stops matching what it must match, the run FAILS before scanning;
  * every pattern is assembled from fragments at import time, so this file
    contains no denied literal and can therefore be scanned by itself. An
    exemption for the scanner would be a hole exactly the size of the scanner.
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import Result, list_files, repo_root  # noqa: E402

MAX_BYTES = 2 * 1024 * 1024

# --- fragment assembly ------------------------------------------------------
# Joined at runtime so the literal never appears in this file's own bytes.
_J = "".join


def frag(*parts):
    return _J(parts)


DENY = [
    ("private git host", re.compile(frag("gond", "olin"), re.I)),
    ("tailnet name", re.compile(frag("tail", "f4273"), re.I)),
    ("tailnet domain", re.compile(re.escape(frag(".ts", ".net")), re.I)),
    ("device name", re.compile(frag("Cachy", r"[-_]?ProArt"), re.I)),
    ("device name", re.compile(frag("defcon", r"[-_]?mini"), re.I)),
    ("device name", re.compile(frag(r"\bstompy", r"\d"), re.I)),
    ("device name", re.compile(frag(r"\btower", r"859\b"), re.I)),
    ("operator username", re.compile(frag(r"\bpmcda", r"de\b"), re.I)),
    ("private knowledge base", re.compile(frag("chief", "-of-staff"), re.I)),
    ("RFC1918 address", re.compile(r"\b10\.\d{1,3}\.\d{1,3}\.\d{1,3}\b")),
    ("RFC1918 address", re.compile(r"\b192\.168\.\d{1,3}\.\d{1,3}\b")),
    ("RFC1918 address", re.compile(r"\b172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}\b")),
    ("CGNAT/tailnet address", re.compile(r"\b100\.(6[4-9]|[7-9]\d|1[01]\d|12[0-7])\.\d{1,3}\.\d{1,3}\b")),
    ("real home path", re.compile(r"/home/(?!runner\b)[A-Za-z0-9._-]+")),
    ("real home path", re.compile(r"/Users/(?!runner\b)[A-Za-z0-9._-]+")),
]

# Canary text: one instance of every denied form, built from the same fragments.
# The addresses and paths are assembled too, not written literally -- spelling a
# private address out here, even inside a comment, would make this file its own
# first finding, and the only way to silence that would be to exempt the scanner
# from the scan. (That is not hypothetical: this comment used to name one.)
_o = str  # keeps the octets below from reading as an address to a grep


def octets(*n):
    return ".".join(_o(x) for x in n)


CANARY = "\n".join([
    frag("gond", "olin") + frag(".tail", "f4273") + frag(".ts", ".net"),
    frag("Cachy", "-ProArt"),
    frag("defcon", "-mini"),
    frag("stompy", "1"),
    frag("tower", "859"),
    frag("pmcda", "de"),
    frag("chief", "-of-staff"),
    octets(10, 0, 0, 4),
    octets(192, 168, 1, 12),
    octets(172, 16, 9, 9),
    octets(100, 106, 129, 23),
    frag("/ho", "me/") + "someone/work",
    frag("/Us", "ers/") + "someone/work",
])

BENIGN = "\n".join([
    "https://forgejo.example.org/api/v1/user",
    "version 1.2.0, 20 operations, " + octets(100, 200) + " is not an address",
    "/path/to/forgejo-cli and " + frag("/ho", "me/") + "runner/work on a CI runner",
    "petejm publishes this plugin",
])

URL = re.compile(r"https?://([A-Za-z0-9._-]+)")
ALLOWED_HOSTS = (
    "example.com", "example.org", "example.net",
    "github.com", "docs.anthropic.com", "code.claude.com", "claude.com",
    "anthropic.com", "forgejo.org", "codeberg.org", "gitea.com",
    "json.schemastore.org", "opensource.org", "spdx.org", "passwordstore.org",
)


def host_allowed(host):
    host = host.lower().rstrip(".")
    for allowed in ALLOWED_HOSTS:
        if host == allowed or host.endswith("." + allowed):
            return True
    return False


def scan(text):
    hits = []
    for n, line in enumerate(text.split("\n"), 1):
        for label, pat in DENY:
            m = pat.search(line)
            if m:
                hits.append((n, label, m.group(0)))
    return hits


def main():
    root = repo_root()
    res = Result("safety")

    # --- canary self-test (fail closed before scanning anything) -----------
    canary_hits = set(label for _, label, _ in scan(CANARY))
    expected = set(label for label, _ in DENY)
    missing = sorted(expected - canary_hits)
    if missing:
        res.fail(
            "safety/self-test",
            "deny patterns failed to match their own canary: %s -- the scan is broken "
            "and MUST NOT be reported as clean" % ", ".join(missing),
        )
    benign_hits = scan(BENIGN)
    if benign_hits:
        res.fail(
            "safety/self-test",
            "deny patterns matched benign text: %s" % benign_hits,
        )
    if res.failures:
        return res.finish()
    res.note("self-test: %d deny pattern(s) verified against canary and benign text" % len(DENY))

    # --- file inventory (fail closed when there is nothing to scan) --------
    files = list_files(root)
    if not files:
        res.fail("safety", "found no files to scan -- refusing to report a clean tree")
        return res.finish()
    md = [f for f in files if f.endswith(".md")]
    if len(files) < 5 or len(md) < 3:
        res.fail(
            "safety",
            "file inventory is implausibly small (%d files, %d markdown) -- refusing to "
            "report a clean tree" % (len(files), len(md)),
        )
        return res.finish()

    scanned = 0
    for rel in files:
        path = os.path.join(root, rel)
        try:
            if os.path.getsize(path) > MAX_BYTES:
                res.note("skipped %s (larger than %d bytes)" % (rel, MAX_BYTES))
                continue
            with open(path, "rb") as fh:
                raw = fh.read()
        except (IOError, OSError) as exc:
            res.fail(rel, "could not be read for scanning: %s" % exc)
            continue
        if b"\x00" in raw:
            res.note("skipped %s (binary)" % rel)
            continue
        scanned += 1
        text = raw.decode("utf-8", "replace")
        for n, label, hit in scan(text):
            res.fail("%s:%d" % (rel, n), "%s must not appear in a public repo: %r" % (label, hit))
        for n, line in enumerate(text.split("\n"), 1):
            for m in URL.finditer(line):
                host = m.group(1)
                if not host_allowed(host):
                    res.fail(
                        "%s:%d" % (rel, n),
                        "URL host %r is not on the public-example allowlist; use an "
                        "example.org/example.com placeholder" % host,
                    )

    if scanned == 0:
        res.fail("safety", "scanned zero files -- refusing to report a clean tree")
    else:
        res.note("scanned %d file(s)" % scanned)

    return res.finish()


if __name__ == "__main__":
    sys.exit(main())
