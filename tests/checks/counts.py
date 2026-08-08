"""Operation-inventory invariants.

DEVELOPMENT.md states the contract in prose: "Keep references/endpoints.md in
sync with SKILL.md Section 4 -- both list the 20 supported operations and their
DESTRUCTIVE classifications." Prose does not fail a build. This does.

The operation count is asserted as a bare literal in several files at once, so
adding or removing one operation is a multi-file edit that is easy to do
incompletely. Everything here is derived from endpoints.md, which is the
enumerated source, and then compared against every place a number is claimed.
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import HISTORICAL, Result, markdown_files, read, repo_root  # noqa: E402

ENDPOINTS = "skills/forgejo-api/references/endpoints.md"
SKILL = "skills/forgejo-api/SKILL.md"
README = "README.md"

ITEM = re.compile(r"^### +(\d+)\. +(.+?)\s*$")
GROUP = re.compile(r"^## +(.+?) +\((\d+) +operations?\)")
ENDPOINT_CODE = re.compile(r"`(GET|POST|PATCH|PUT|DELETE) +(/api/v1[^`]*)`")
SKILL_BULLET = re.compile(r"^- +`(GET|POST|PATCH|PUT|DELETE) +(/api/v1[^`]*)`")
SKILL_GROUP = re.compile(r"^\*\*(.+?)\*\*\s*$")
README_ROW = re.compile(r"^\| *\*\*(.+?)\*\* *\|.*?\| *(\d+) *\|\s*$")
DECLARED_A = re.compile(r"(\d+) +(?:built-in +|supported +)?operations\b")
DECLARED_B = re.compile(r"\bsupported +(\d+)\b")
ENDPOINT_CLAIM = re.compile(r"\b\d{3}-endpoint\b")


def normalise(method, path):
    return "%s %s" % (method, path.split("?", 1)[0].rstrip("/"))


def parse_endpoints(res, root):
    text = read(root, ENDPOINTS)
    lines = text.split("\n")
    items = []          # (number, title, endpoint, destructive)
    groups = []         # (name, declared, counted)
    cur_group = None
    cur_item = None

    def close_item():
        if cur_item is None:
            return
        num, title, body = cur_item
        ep = None
        for line in body:
            m = ENDPOINT_CODE.search(line)
            if m:
                ep = normalise(m.group(1), m.group(2))
                break
        destructive = any("**DESTRUCTIVE" in line for line in body)
        if ep is None:
            res.fail("%s" % ENDPOINTS, "operation %s (%s) has no `METHOD /api/v1/...` line" % (num, title))
        items.append((num, title, ep, destructive))
        if groups:
            groups[-1][2].append(num)

    for line in lines:
        g = GROUP.match(line)
        if g:
            close_item()
            cur_item = None
            groups.append([g.group(1).strip(), int(g.group(2)), []])
            cur_group = g.group(1)
            continue
        i = ITEM.match(line)
        if i:
            close_item()
            cur_item = (int(i.group(1)), i.group(2), [])
            continue
        if line.startswith("## "):
            close_item()
            cur_item = None
            cur_group = None
            continue
        if cur_item is not None:
            cur_item[2].append(line)
    close_item()

    for name, declared, members in groups:
        if declared != len(members):
            res.fail(
                ENDPOINTS,
                "group heading '%s' claims %d operation(s) but %d follow it"
                % (name, declared, len(members)),
            )

    numbers = [n for n, _, _, _ in items]
    if numbers != list(range(1, len(numbers) + 1)):
        res.fail(ENDPOINTS, "operation numbering is not contiguous 1..N: %s" % numbers)

    return items


def parse_skill(res, root):
    text = read(root, SKILL)
    lines = text.split("\n")
    inside = False
    group = ""
    ops = []
    for line in lines:
        if line.startswith("## Section 4"):
            inside = True
            continue
        if inside and line.startswith("## "):
            break
        if not inside:
            continue
        g = SKILL_GROUP.match(line.strip())
        if g:
            group = g.group(1)
            continue
        b = SKILL_BULLET.match(line)
        if b:
            ep = normalise(b.group(1), b.group(2))
            destructive = "DESTRUCTIVE" in line or "DESTRUCTIVE" in group
            ops.append((ep, destructive))
    if not ops:
        res.fail(SKILL, "Section 4 lists no operations -- heading may have been renamed")
    return ops


def main():
    root = repo_root()
    res = Result("counts")

    for rel in (ENDPOINTS, SKILL, README):
        if not os.path.exists(os.path.join(root, rel)):
            res.fail(rel, "required file is missing")
            return res.finish()

    items = parse_endpoints(res, root)
    total = len(items)
    if total == 0:
        res.fail(ENDPOINTS, "no numbered operations found -- extraction is probably broken")
        return res.finish()
    res.note("endpoints.md enumerates %d operation(s)" % total)

    skill_ops = parse_skill(res, root)
    if len(skill_ops) != total:
        res.fail(
            SKILL,
            "Section 4 lists %d operation(s) but %s enumerates %d"
            % (len(skill_ops), ENDPOINTS, total),
        )

    ep_set = set(ep for _, _, ep, _ in items if ep)
    sk_set = set(ep for ep, _ in skill_ops)
    for missing in sorted(ep_set - sk_set):
        res.fail(SKILL, "Section 4 is missing operation %s (present in endpoints.md)" % missing)
    for extra in sorted(sk_set - ep_set):
        res.fail(ENDPOINTS, "endpoints.md is missing operation %s (present in SKILL.md Section 4)" % extra)

    ep_destructive = set(ep for _, _, ep, d in items if d and ep)
    sk_destructive = set(ep for ep, d in skill_ops if d)
    for missing in sorted(ep_destructive - sk_destructive):
        res.fail(SKILL, "operation %s is DESTRUCTIVE in endpoints.md but not in Section 4" % missing)
    for extra in sorted(sk_destructive - ep_destructive):
        res.fail(ENDPOINTS, "operation %s is DESTRUCTIVE in Section 4 but not in endpoints.md" % extra)
    res.note("destructive set: %s" % ", ".join(sorted(ep_destructive)) or "(empty)")

    # --- README category table ---------------------------------------------
    rows = []
    for n, line in enumerate(read(root, README).split("\n"), 1):
        m = README_ROW.match(line)
        if m:
            rows.append((n, m.group(1), int(m.group(2))))
    if not rows:
        res.fail(README, "no '| **Category** | ... | N |' rows found -- table may have been restructured")
    else:
        s = sum(c for _, _, c in rows)
        if s != total:
            res.fail(
                README,
                "supported-operations table Count column sums to %d but endpoints.md enumerates %d"
                % (s, total),
            )

    # --- literal totals asserted in prose ----------------------------------
    declared_sites = 0
    for rel in markdown_files(root, include_historical=False):
        for n, line in enumerate(read(root, rel).split("\n"), 1):
            if line.startswith("## "):
                continue
            for m in list(DECLARED_A.finditer(line)) + list(DECLARED_B.finditer(line)):
                declared_sites += 1
                got = int(m.group(1))
                if got != total:
                    res.fail(
                        "%s:%d" % (rel, n),
                        "claims %d operations but endpoints.md enumerates %d" % (got, total),
                    )
    if declared_sites == 0:
        res.fail("counts", "no prose operation-count claims found at all -- extraction is probably broken")
    else:
        res.note("%d prose operation-count claim(s) cross-checked" % declared_sites)

    # --- version-pinned endpoint-count claims ------------------------------
    for rel in markdown_files(root, include_historical=False):
        for n, line in enumerate(read(root, rel).split("\n"), 1):
            if ENDPOINT_CLAIM.search(line):
                res.fail(
                    "%s:%d" % (rel, n),
                    "hardcodes an instance-specific endpoint count; the API surface is "
                    "version-dependent and must be described, not numbered",
                )
    res.note("historical files exempt from prose claims: %s" % ", ".join(HISTORICAL))

    return res.finish()


if __name__ == "__main__":
    sys.exit(main())
