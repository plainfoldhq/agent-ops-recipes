#!/usr/bin/env python3
"""Watchdog checks for an unattended agent repo. Writes problems.md (empty when healthy).

Runs in a scheduled GitHub Actions job (watchdog.yml) that needs no agent and no secret beyond the
default GITHUB_TOKEN. The workflow opens one alert issue when problems.md is non-empty, comments on
it while problems persist, and closes it when the checks pass again.

    python3 watchdog_checks.py --stale STATE.md:30 --json-field usage.json:weekly_pct \
      --command "tests=python3 -m unittest -q" --out problems.md

    --stale PATH:HOURS      problem if no git commit touched PATH in HOURS (agent runs stopped)
    --json-field FILE:KEY   problem if KEY is missing/null or the file has a non-empty "error"
    --command NAME=CMD      problem if CMD exits non-zero (last 15 output lines are included)

Every check is optional and repeatable. Exit code is 0 unless the arguments are invalid; the workflow
decides from problems.md. Standard library + git.
"""
import argparse
import json
import subprocess
import sys
import time


def git_age_hours(path, repo=".", now=None):
    r = subprocess.run(["git", "log", "-1", "--format=%ct", "--", path], cwd=repo,
                       capture_output=True, text=True)
    if r.returncode != 0 or not r.stdout.strip():
        return None
    return ((now or time.time()) - int(r.stdout.strip())) / 3600


def check_stale(spec, repo=".", now=None):
    path, _, hours = spec.rpartition(":")
    if not path or not hours.isdigit():
        raise SystemExit(f"--stale wants PATH:HOURS, got {spec!r}")
    age = git_age_hours(path, repo, now)
    if age is None:
        return f"{path}: no commit touches this file"
    if age > int(hours):
        return f"{path} last changed {int(age)} h ago (limit {hours} h): the scheduled agent runs may be disabled or failing."
    return None


def check_json_field(spec, repo="."):
    path, _, field = spec.rpartition(":")
    if not path or not field:
        raise SystemExit(f"--json-field wants FILE:FIELD, got {spec!r}")
    try:
        with open(f"{repo}/{path}", encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, ValueError) as e:
        return f"{path}: cannot read ({type(e).__name__})"
    if not isinstance(d, dict):
        return f"{path}: not a JSON object"
    if d.get("error"):
        return f"{path}: error = {str(d['error'])[:200]}"
    if d.get(field) is None:
        return f"{path}: {field} is missing or null"
    return None


def check_command(spec, repo=".", timeout=600):
    name, sep, cmd = spec.partition("=")
    if not sep or not name.strip() or not cmd.strip():
        raise SystemExit(f"--command wants NAME=COMMAND, got {spec!r}")
    try:
        r = subprocess.run(cmd, shell=True, cwd=repo, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return f"{name}: timed out after {timeout} s"
    if r.returncode == 0:
        return None
    tail = "\n".join((r.stdout + r.stderr).strip().splitlines()[-15:])
    return f"{name}: exit {r.returncode}\n```\n{tail}\n```"


def run(args, repo=".", now=None):
    problems = []
    for s in args.stale:
        problems.append(check_stale(s, repo, now))
    for s in args.json_field:
        problems.append(check_json_field(s, repo))
    for s in args.command:
        problems.append(check_command(s, repo, args.timeout))
    return [p for p in problems if p]


def main(argv=None, repo=".", out=print):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--stale", action="append", default=[], metavar="PATH:HOURS")
    ap.add_argument("--json-field", action="append", default=[], metavar="FILE:FIELD")
    ap.add_argument("--command", action="append", default=[], metavar="NAME=COMMAND")
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("--out", default="problems.md")
    args = ap.parse_args(argv)
    problems = run(args, repo)
    with open(f"{repo}/{args.out}" if not args.out.startswith("/") else args.out, "w", encoding="utf-8") as f:
        f.write("".join(f"- {p}\n" for p in problems))
    out(f"{len(problems)} problem(s)")
    for p in problems:
        out("- " + p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
