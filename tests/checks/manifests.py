"""Manifest, version-lock and licence checks.

Rationale: CHANGELOG.md:17 records that plugin.json was left at 1.0.0 after the
v1.1.0 changes shipped. A version that disagrees with the newest changelog
heading is exactly the class of defect a five-line check catches for free, and
it has already happened once in this repo.
"""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import Result, read, repo_root  # noqa: E402

SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
HEADING = re.compile(r"^## +v(\d+\.\d+\.\d+) +\S+ +(\d{4}-\d{2}-\d{2})\s*$")
LOOSE_HEADING = re.compile(r"^## +v?(\d+\.\d+\.\d+)")


def semver_key(v):
    return tuple(int(x) for x in v.split("."))


def load_json(res, root, rel):
    path = os.path.join(root, rel)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r") as fh:
            return json.load(fh)
    except ValueError as exc:
        res.fail(rel, "not valid JSON: %s" % exc)
        return None


def main():
    root = repo_root()
    res = Result("manifests")

    plugin = load_json(res, root, ".claude-plugin/plugin.json")
    if plugin is None:
        res.fail(".claude-plugin/plugin.json", "missing or unparseable (required)")
        return res.finish()

    for field in ("name", "version", "description"):
        if not plugin.get(field):
            res.fail(".claude-plugin/plugin.json", "missing required field %r" % field)

    version = plugin.get("version", "")
    if not SEMVER.match(str(version)):
        res.fail(".claude-plugin/plugin.json", "version %r is not X.Y.Z" % version)

    # --- changelog headings -------------------------------------------------
    changelog = None
    if os.path.exists(os.path.join(root, "CHANGELOG.md")):
        changelog = read(root, "CHANGELOG.md")
    else:
        res.fail("CHANGELOG.md", "missing (version lock cannot be verified)")

    newest = None
    if changelog is not None:
        seen = []
        for n, line in enumerate(changelog.split("\n"), 1):
            loose = LOOSE_HEADING.match(line)
            if not loose:
                continue
            if not HEADING.match(line):
                res.fail(
                    "CHANGELOG.md:%d" % n,
                    "release heading is not '## vX.Y.Z <sep> YYYY-MM-DD': %r" % line.strip(),
                )
            seen.append((n, loose.group(1)))
        if not seen:
            res.fail("CHANGELOG.md", "no '## vX.Y.Z' release heading found")
        else:
            newest = seen[0][1]
            ordered = [v for _, v in seen]
            if ordered != sorted(ordered, key=semver_key, reverse=True):
                res.fail("CHANGELOG.md", "release headings are not newest-first: %s" % ordered)

    if newest is not None and str(version) != newest:
        res.fail(
            ".claude-plugin/plugin.json",
            "version %r != newest CHANGELOG heading v%s" % (version, newest),
        )

    # --- marketplace --------------------------------------------------------
    mkt_rel = ".claude-plugin/marketplace.json"
    mkt = load_json(res, root, mkt_rel)
    if mkt is None and os.path.exists(os.path.join(root, mkt_rel)):
        return res.finish()
    if mkt is None:
        res.note("%s absent -- marketplace version lock skipped" % mkt_rel)
    else:
        entries = mkt.get("plugins")
        if not isinstance(entries, list) or not entries:
            res.fail(mkt_rel, "'plugins' must be a non-empty list")
            entries = []
        matched = [e for e in entries if e.get("name") == plugin.get("name")]
        if not matched:
            res.fail(
                mkt_rel,
                "no entry named %r (plugin.json name)" % plugin.get("name"),
            )
        for e in matched:
            if e.get("version") != version:
                res.fail(
                    mkt_rel,
                    "entry %r version %r != plugin.json version %r"
                    % (e.get("name"), e.get("version"), version),
                )
            if e.get("license") and plugin.get("license") and e["license"] != plugin["license"]:
                res.fail(
                    mkt_rel,
                    "entry license %r != plugin.json license %r"
                    % (e["license"], plugin["license"]),
                )

    # --- licence file -------------------------------------------------------
    declared = plugin.get("license")
    lic_path = None
    for cand in ("LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING"):
        if os.path.exists(os.path.join(root, cand)):
            lic_path = cand
            break
    if lic_path is None:
        res.fail("LICENSE", "no licence file, but plugin.json declares license %r" % declared)
    elif declared:
        body = read(root, lic_path)
        head = body[:400]
        # Only assert what the file itself says; do not guess a licence family.
        if declared.upper() == "MIT" and "MIT License" not in head:
            res.fail(lic_path, "plugin.json declares MIT but the file does not say 'MIT License'")

    return res.finish()


if __name__ == "__main__":
    sys.exit(main())
