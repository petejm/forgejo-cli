"""Eval-suite structure checks.

Two layouts are accepted because the repo has carried both: a single
`evals/evals.json` array, and the per-case directory layout that
`claude plugin eval` discovers (`evals/<case>/prompt.md` plus `graders/*.md`).
Whichever is present must be well formed, and at least one case must exist --
an eval directory that has quietly emptied itself is the failure mode this
guards against.
"""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import Result, read, repo_root  # noqa: E402

KEBAB = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def check_json_form(res, root, rel):
    try:
        with open(os.path.join(root, rel), "r") as fh:
            data = json.load(fh)
    except ValueError as exc:
        res.fail(rel, "not valid JSON: %s" % exc)
        return 0
    if not isinstance(data, list):
        res.fail(rel, "expected a JSON array of cases, got %s" % type(data).__name__)
        return 0
    if not data:
        res.fail(rel, "eval array is empty")
        return 0
    seen = set()
    for i, case in enumerate(data):
        where = "%s[%d]" % (rel, i)
        if not isinstance(case, dict):
            res.fail(where, "case is not an object")
            continue
        cid = case.get("id")
        if not cid:
            res.fail(where, "missing 'id'")
        else:
            if not KEBAB.match(str(cid)):
                res.fail(where, "id %r is not kebab-case" % cid)
            if cid in seen:
                res.fail(where, "duplicate id %r" % cid)
            seen.add(cid)
        for field in ("description", "prompt", "expected"):
            if not case.get(field):
                res.fail(where, "missing or empty %r" % field)
        exp = case.get("expected")
        if isinstance(exp, dict):
            ep = exp.get("endpoint") or exp.get("endpoint_pattern")
            if ep and not str(ep).startswith("/api/v1"):
                res.fail(where, "endpoint %r does not start with /api/v1" % ep)
    return len(data)


def check_dir_form(res, root):
    evals_dir = os.path.join(root, "evals")
    cases = 0
    for name in sorted(os.listdir(evals_dir)):
        case_dir = os.path.join(evals_dir, name)
        if not os.path.isdir(case_dir):
            continue
        prompt = os.path.join(case_dir, "prompt.md")
        if not os.path.exists(prompt):
            res.fail("evals/%s" % name, "directory has no prompt.md")
            continue
        cases += 1
        if not KEBAB.match(name):
            res.fail("evals/%s" % name, "case id is not kebab-case")
        if not read(root, "evals/%s/prompt.md" % name).strip():
            res.fail("evals/%s/prompt.md" % name, "prompt is empty")
        graders_dir = os.path.join(case_dir, "graders")
        if not os.path.isdir(graders_dir):
            res.fail("evals/%s" % name, "no graders/ directory -- nothing would be scored")
            continue
        graders = [g for g in sorted(os.listdir(graders_dir)) if g.endswith(".md")]
        if not graders:
            res.fail("evals/%s/graders" % name, "no *.md grader files")
        for g in graders:
            if not read(root, "evals/%s/graders/%s" % (name, g)).strip():
                res.fail("evals/%s/graders/%s" % (name, g), "grader file is empty")
    return cases


def main():
    root = repo_root()
    res = Result("evals")

    if not os.path.isdir(os.path.join(root, "evals")):
        res.fail("evals/", "directory is missing")
        return res.finish()

    total = 0
    json_form = os.path.join(root, "evals", "evals.json")
    if os.path.exists(json_form):
        n = check_json_form(res, root, "evals/evals.json")
        res.note("evals.json layout: %d case(s)" % n)
        total += n

    n = check_dir_form(res, root)
    if n:
        res.note("per-case directory layout: %d case(s)" % n)
    total += n

    if total == 0:
        res.fail("evals/", "no eval cases found in either supported layout")

    return res.finish()


if __name__ == "__main__":
    sys.exit(main())
