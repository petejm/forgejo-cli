"""Checks on the shell examples the plugin teaches Claude to run.

This repo's product is shell that an agent will copy and execute, so a defect in
a fenced example is a defect in the product.

Two design notes, both learned by getting them wrong first:

  * Use is not mention. These docs deliberately discuss the hazards they guard
    against ("Never `$USER` -- every login shell exports it"), and a naive
    literal scan flags the warning as the defect. Inside a ```bash fence,
    everything is code. Outside one, only a use-position match counts.

  * A pattern check that stops matching after a refactor is worse than no
    check. When the netrc examples moved from `<(echo "machine $HOST ...")` to
    `<(printf 'machine %s ...' "$HOST" ...)`, a matcher anchored on the old
    spelling silently verified nothing and reported clean. Every check here
    reports how many sites it actually inspected, and fails when it cannot
    identify a netrc host rather than passing by default.
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import Result, bash_fences, logical_commands, markdown_files, read, repo_root  # noqa: E402

IS_CURL = re.compile(r"(^|[;&|(]|\$\()\s*curl\b")
# A standalone `...` marks an illustrative fragment (`curl ... -H x`,
# `--netrc-file <(echo ...)`), not a runnable command. Bounded so a real
# filename or ellipsis inside a word is not mistaken for an elision.
ELISION = re.compile(r"(?<![.\w])\.\.\.(?![.\w])")
INLINE_CODE = re.compile(r"`([^`\n]+)`")

# `$USER` anywhere inside a fence is code. Outside a fence it only counts when
# it sits in a value position -- immediately after `login`, `machine`, or in a
# `/users/` path -- which is where the wrong-account bug actually happens.
USER_ANY = re.compile(r"(?<![A-Za-z0-9_])\$\{?USER\}?(?![A-Za-z0-9_])")
USER_USE = re.compile(r"(?:login|machine|/users/)\s*\"?\$\{?USER\}?(?![A-Za-z0-9_])")

NETRC_SITE = "--netrc-file <("
MACHINE_VAR = re.compile(r"machine\s+\$\{?([A-Za-z_]\w*)\}?")
MACHINE_FMT = re.compile(r"machine\s+%s")
FIRST_VAR_ARG = re.compile(r"\"\$\{?([A-Za-z_]\w*)\}?\"")
ASSIGN = re.compile(r"^\s*([A-Za-z_]\w*)=(.+)$")

# Constructs that remove a `:port` suffix from a host string. curl matches the
# netrc `machine` token against the bare host: give it `host:port` and it
# matches nothing and sends no Authorization header at all.
PORT_STRIP = re.compile(
    r"%%:"                                   # ${HOST%%:*}
    r"|cut\s+-d\s*['\"]?:"                   # cut -d:
    r"|awk\s+-F\s*['\"]?:"                   # awk -F:
    r"|\[[^\]]*:[^\]]*\]\s*\.\*"             # sed 's|[/:].*||'
    r"|s([|/#,])\^?:[^|/#,]*\.\*\1"          # sed 's|:.*||'
    r"|:\[0-9\]\*\$"                         # sed 's/:[0-9]*$//'
)


def code_texts(text):
    """Yield (line, text, in_fence) for every copyable code region."""
    for start, body in bash_fences(text):
        for lineno, cmd in logical_commands(body, start):
            yield lineno, cmd, True
    inside = False
    for n, line in enumerate(text.split("\n"), 1):
        if line.strip().startswith("```"):
            inside = not inside
            continue
        if inside:
            continue
        for m in INLINE_CODE.finditer(line):
            yield n, m.group(1), False


def main():
    root = repo_root()
    res = Result("shellfences")
    docs = markdown_files(root)
    if not docs:
        res.fail("shellfences", "no markdown files found -- the check had nothing to verify")
        return res.finish()

    # --- curl timeout hygiene ----------------------------------------------
    curl_seen = 0
    curl_elided = 0
    for rel in docs:
        for start, body in bash_fences(read(root, rel)):
            for lineno, cmd in logical_commands(body, start):
                if cmd.strip().startswith("#") or not IS_CURL.search(cmd):
                    continue
                if ELISION.search(cmd):
                    # `curl ... -H ...` is an illustrative fragment, not a
                    # runnable command; there is nothing to time out.
                    curl_elided += 1
                    continue
                curl_seen += 1
                missing = [f for f in ("--connect-timeout", "--max-time") if f not in cmd]
                if missing:
                    res.fail(
                        "%s:%d" % (rel, lineno),
                        "curl example without %s -- an agent running this can hang forever"
                        % " and ".join(missing),
                    )
    if curl_seen == 0:
        res.fail("shellfences", "no runnable curl examples found -- fence extraction is probably broken")
    else:
        res.note("%d runnable curl example(s) inspected, %d elided fragment(s) skipped"
                 % (curl_seen, curl_elided))

    # --- $USER collision ----------------------------------------------------
    user_sites = 0
    for rel in markdown_files(root, include_historical=False):
        for lineno, chunk, in_fence in code_texts(read(root, rel)):
            hit = USER_ANY.search(chunk) if in_fence else USER_USE.search(chunk)
            if hit:
                user_sites += 1
                res.fail(
                    "%s:%d" % (rel, lineno),
                    "uses $USER (the OS username) where the Forgejo username is meant. "
                    "Every login shell exports USER, so it never trips an unset guard -- "
                    "it silently authenticates as the wrong account. Use $FORGEJO_USER "
                    "or the $OP_USER the auth section resolves.",
                )
    if user_sites == 0:
        res.note("no $USER use-sites in code")

    # --- netrc generation ---------------------------------------------------
    host_vars = set()
    netrc_sites = 0
    netrc_elided = 0
    for rel in docs:
        for lineno, chunk, _in_fence in code_texts(read(root, rel)):
            if NETRC_SITE not in chunk:
                continue
            if ELISION.search(chunk):
                netrc_elided += 1
                continue
            netrc_sites += 1
            where = "%s:%d" % (rel, lineno)

            # netrc is whitespace-tokenised: an unquoted value is truncated at
            # the first space, and the request goes out with a shorter, wrong
            # password. curl supports quoted strings since 7.84.0.
            for field in ("login", "password"):
                if not re.search(r"%s\s+\\?[\"']" % field, chunk):
                    res.fail(
                        where,
                        "netrc %s value is not quoted; netrc is whitespace-delimited, so a "
                        "value containing a space is silently truncated at the space" % field,
                    )

            direct = MACHINE_VAR.search(chunk)
            if direct:
                host_vars.add((where, direct.group(1)))
            elif MACHINE_FMT.search(chunk):
                tail = chunk[MACHINE_FMT.search(chunk).end():]
                arg = FIRST_VAR_ARG.search(tail)
                if arg is None:
                    res.fail(where, "cannot identify the netrc machine host argument -- "
                                    "port stripping is unverifiable here")
                else:
                    host_vars.add((where, arg.group(1)))
            else:
                res.fail(where, "netrc entry has no recognisable `machine` token -- "
                                "port stripping is unverifiable here")

    if netrc_sites == 0:
        res.fail("shellfences", "no netrc generation sites found -- this repo documents basic "
                                "auth via netrc, so extraction is probably broken")
    else:
        res.note("%d netrc generation site(s) inspected, %d elided mention(s) skipped"
                 % (netrc_sites, netrc_elided))

    # Host variables are resolved repo-wide: a snippet may legitimately defer
    # the assignment to the canonical auth section, but *somewhere* the variable
    # must be defined, and every definition must strip the port.
    assignments = {}
    for rel in docs:
        for start, body in bash_fences(read(root, rel)):
            for lineno, cmd in logical_commands(body, start):
                m = ASSIGN.match(cmd)
                if m:
                    assignments.setdefault(m.group(1), []).append(("%s:%d" % (rel, lineno), m.group(2)))

    checked = 0
    for where, var in sorted(host_vars):
        defs = assignments.get(var, [])
        if not defs:
            res.fail(where, "netrc machine host $%s is never assigned anywhere in the repo, "
                            "so it cannot be shown to have its port stripped" % var)
            continue
        for def_where, expr in defs:
            if "://" not in expr and "_URL" not in expr:
                continue
            checked += 1
            if not PORT_STRIP.search(expr):
                res.fail(
                    def_where,
                    "$%s is derived from a URL but never has a ':port' suffix removed. curl "
                    "matches the netrc 'machine' token against the bare host, so a non-default "
                    "port produces no Authorization header at all -- which surfaces as an auth "
                    "failure, not a config error." % var,
                )
    if host_vars and checked == 0:
        res.fail("shellfences", "no netrc host assignment was derived from a URL -- port-strip "
                                "verification inspected nothing")
    else:
        res.note("%d netrc host assignment(s) verified for port stripping" % checked)

    return res.finish()


if __name__ == "__main__":
    sys.exit(main())
