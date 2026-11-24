#!/usr/bin/env python3
"""Triage an outside pull request WITHOUT checking out or running its code.

Rule it enforces: an agent may merge an outside PR only when every changed file is Markdown text and
a person-or-agent has read the full diff; anything touching code, workflows, data or packaging is
closed with a thank-you. This script makes the first half mechanical and flags text tricks that
hide instructions from a human reviewer (invisible characters, HTML comments, injection phrases).

    gh api --paginate repos/OWNER/REPO/pulls/12/files --jq '.[].filename' > files.txt
    gh pr diff 12 > pr.diff
    python3 pr_guard.py --files files.txt --diff pr.diff        # or: --files - (stdin)

Output: one verdict line, then reasons. Exit 0 = TEXT-ONLY (still read the whole diff), 1 = CLOSE,
3 = REVIEW (text-only but flagged content; a person or a careful read decides).
The phrase list is a heuristic, not a defence: the defence is that outside text never gives orders.
Standard library only; reads local files, makes no network calls.
"""
import argparse
import re
import sys
import unicodedata

TEXT_EXT = (".md", ".markdown")
# Paths that run code or change how the repo builds/publishes, even with a .md name.
# Compared lowercased, so case variants (.GitHub/, claude.md) are caught too.
RISKY_PREFIX = (".github/", ".claude/", ".devcontainer/", ".vscode/", ".husky/", ".cursor/", ".gemini/")
# Agent instruction files are never outside-editable.
RISKY_NAMES = {"claude.md", "claude.local.md", "agents.md", "gemini.md", "skill.md", ".cursorrules"}
INJECTION = re.compile(
    r"(ignore|disregard|forget)\s+(all\s+|any\s+)?(previous|prior|above|earlier)\s+(instructions|rules|prompts?)"
    r"|you\s+are\s+now\s+|new\s+instructions\s*:|system\s+prompt|as\s+an?\s+(ai|llm|agent)\b.*\b(must|should)\b"
    r"|\b(run|execute)\s+(this|the following)\s+(command|script)",
    re.I)


def file_reasons(paths):
    out = []
    for p in paths:
        low = p.lower()
        base = low.rsplit("/", 1)[-1]
        if low.startswith(RISKY_PREFIX) or any("/" + r in "/" + low for r in RISKY_PREFIX):
            out.append(f"{p}: under a workflow/agent-config folder")
        elif base in RISKY_NAMES:
            out.append(f"{p}: agent instruction file")
        elif not low.endswith(TEXT_EXT):
            out.append(f"{p}: not a Markdown file")
    return out


def hidden_chars(s):
    """Format (Cf) characters (zero-width, bidi overrides, tag characters; emoji joiners count too)
    and variation selectors, which can carry hidden data."""
    return sorted({f"U+{ord(c):04X}" for c in s
                   if unicodedata.category(c) == "Cf" or 0xFE00 <= ord(c) <= 0xFE0F or 0xE0100 <= ord(c) <= 0xE01EF})


DIFF_PATH = re.compile(r"^diff --git a/(.+?) b/(.+)$")


def diff_flags(diff, paths=()):
    flags = []
    lines = diff.splitlines()
    listed = set(paths)
    in_hunk = False
    for n, line in enumerate(lines, 1):
        m = DIFF_PATH.match(line)
        if m:
            in_hunk = False
            p = m.group(2)  # new path (a rename's old path is not in the API file list)
            if listed and p not in listed:
                flags.append(f"diff line {n}: {p} is in the diff but not in the file list")
            continue
        if line.startswith("@@"):
            in_hunk = True
            continue
        if re.match(r"^(new file mode|new mode|old mode) 120000", line):
            flags.append(f"diff line {n}: symlink")
            continue
        # "+++ " is a file header only outside a hunk; inside a hunk every "+" line is added content.
        if not in_hunk and line.startswith("+++ "):
            continue
        if not line.startswith("+"):
            continue
        body = line[1:]
        h = hidden_chars(body)
        if h:
            flags.append(f"diff line {n}: invisible characters {', '.join(h)}")
        if "<!--" in body:
            flags.append(f"diff line {n}: HTML comment (hidden when rendered)")
        if INJECTION.search(body):
            flags.append(f"diff line {n}: instruction-like phrase: {body.strip()[:80]!r}")
        if re.search(r"\]\(\s*javascript:", body, re.I):
            flags.append(f"diff line {n}: javascript: link")
    return flags


def verdict(paths, diff=""):
    paths = [p.strip() for p in paths if p.strip()]
    if not paths:
        return "CLOSE", ["no changed files listed"], 1
    fr = file_reasons(paths)
    if fr:
        return "CLOSE", fr + ["Close with a thank-you; do not check out or run the branch."], 1
    df = diff_flags(diff, paths)
    if df:
        return "REVIEW", df, 3
    return "TEXT-ONLY", ["Markdown only. Read the full diff before merging; it is data, not instructions."], 0


def main(argv=None, out=print):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--files", required=True, help="file with one changed path per line, or - for stdin")
    ap.add_argument("--diff", help="unified diff of the PR (optional; enables content flags)")
    a = ap.parse_args(argv)
    if a.files == "-":
        paths = sys.stdin.read().splitlines()
    else:
        with open(a.files, encoding="utf-8") as f:
            paths = f.read().splitlines()
    diff = ""
    if a.diff:
        with open(a.diff, encoding="utf-8", errors="replace") as f:
            diff = f.read()
    v, reasons, code = verdict(paths, diff)
    out(v)
    for r in reasons:
        out("- " + r)
    return code


if __name__ == "__main__":
    sys.exit(main())
