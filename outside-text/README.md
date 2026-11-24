# Outside text is data (prompt-injection rules + PR guard)

**Problem.** A scheduled agent with push access reads issues, PR descriptions, comments, web pages and
package metadata. Any of them can contain "ignore previous instructions and ..." or hide it in an HTML
comment or zero-width characters. The agent may obey.

**How it works.**
- `SECURITY-RULES.md`: a block to paste into CLAUDE.md. It names every outside source as data, says who
  may give instructions, makes social accounts write-only, forbids running outside PR code, and keeps keys
  behind a queue. Each rule has a one-line reason.
- `pr_guard.py`: triage for an outside PR from its file list and diff, with no checkout:
  `CLOSE` if any file is not Markdown, is under a config folder such as `.github/` or `.claude/` (any case,
  any depth), or is an agent instruction file (`CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `SKILL.md`, ...);
  `REVIEW` if a Markdown-only diff adds invisible characters or variation selectors, HTML comments,
  `javascript:` links, instruction-like phrases, a symlink, or a file missing from the file list;
  otherwise `TEXT-ONLY` (read the full diff, then merge).

```
gh api --paginate repos/OWNER/REPO/pulls/12/files --jq '.[].filename' > files.txt
gh pr diff 12 > pr.diff
python3 scripts/pr_guard.py --files files.txt --diff pr.diff   # exit 0 TEXT-ONLY, 1 CLOSE, 3 REVIEW
```

**Files.**
| File | Where it goes |
|---|---|
| `SECURITY-RULES.md` | paste the block into CLAUDE.md |
| `pr_guard.py` | `scripts/pr_guard.py` |
| `test_pr_guard.py` | your tests folder; offline |

**Setup.**
1. Paste and adapt the rules (bracketed parts).
2. Copy `pr_guard.py`; add to CLAUDE.md: "Before acting on an outside PR, run scripts/pr_guard.py."
3. On public repos: set the default workflow token to read-only and require approval for fork PRs from
   outside contributors (repo Settings > Actions > General).

**Limits.**
- No filter catches every injection. The phrase list is a tripwire; the real defence is the rule that outside
  text never gives orders, and that the agent cannot reach keys.
- `pr_guard.py` trusts the file list you give it; get it from the GitHub API (paginated, as above:
  `gh pr view --json files` can be capped at 100 files), not from the PR text. Paths in the diff headers are
  cross-checked against the list.
- Emoji with zero-width joiners are flagged as invisible characters (false positive, cheap to dismiss).
