# Claude Code agent recipes (free part)

Two patterns for running a scheduled, unattended Claude Code agent from a git repo, from a setup that
runs this way every night. MIT licensed. Not affiliated with or endorsed by Anthropic.

| Folder | Recipe |
|---|---|
| `watchdog/` | Daily GitHub Actions job that opens one "Agent watchdog alert" issue when the agent setup breaks (runs stopped, status file error, failing command) and closes it on recovery. No secrets. |
| `outside-text/` | Prompt-injection rules to paste into CLAUDE.md, and `pr_guard.py`: triage an outside PR from its file list and diff without checking it out (CLOSE / REVIEW / TEXT-ONLY). |

Each folder has a README (problem, how it works, files, setup, limits) and an offline test.
Run all tests: `bash run_tests.sh`. Python 3.9+ standard library, bash, git.

## More
- Usage gate for scheduled runs (reads plan usage only through the official Claude Code CLI in your own
  GitHub Actions workflow): free agent-ops kit core, github.com/plainfoldhq/agent-ops-kit.
- The full recipe pack (paid, https://buy.polar.sh/polar_cl_OGbYBTUGwAY2S9GjG700JFDDBmstD7M0iE7n71S4Ium) adds: a queue-in-repo worker that keeps API keys out of
  the agent's environment (a workflow runs allow-listed actions with the secret), a file-based pipeline with claims for
  parallel child sessions plus the child-session prompt, and a one-call run-start check script. All with tests.

Written with AI assistance. No promise of results.
