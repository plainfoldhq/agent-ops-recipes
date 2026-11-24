# Watchdog issue

**Problem.** An unattended agent fails quietly: the schedule gets disabled, a token expires, a test
starts failing. Nobody notices for days.

**How it works.** A daily GitHub Actions job, separate from the agent, runs a few checks. If any fail it
opens ONE issue titled "Agent watchdog alert" (GitHub notifies repo watchers by email), comments on it
each day it stays broken, and closes it when the checks pass. The agent's CLAUDE.md says: an open alert
issue is the first job of the run.

Checks (`watchdog_checks.py`, all optional and repeatable):
- `--stale STATE.md:30`: no commit touched the file in 30 h, so agent runs have stopped.
- `--json-field usage.json:weekly_pct`: a status file the agent depends on has an `error` or a null field
  (for example an expired token in a usage-check workflow).
- `--command "tests=python3 -m unittest discover -s tests -q"`: any command that must exit 0 (tests, an audit
  script, a link checker). The last 15 output lines go into the issue.

**Files.**
| File | Where it goes |
|---|---|
| `watchdog_checks.py` | `scripts/watchdog_checks.py` |
| `watchdog.yml` | `.github/workflows/watchdog.yml` |
| `test_watchdog.py` | your tests folder; offline, builds a temp git repo with back-dated commits |

**Setup.**
1. Copy the files. Edit the check lines in `watchdog.yml` to your files and commands.
2. Pick a cron time after your agent runs usually finish.
3. Watch the repo (Watch > All activity, or at least Issues) so the alert reaches your email.
4. Add to CLAUDE.md: "If an open 'Agent watchdog alert' issue exists, fixing it is the first job."
5. Run it once by hand (Actions > watchdog > Run workflow) to see an issue open, then fix and re-run to see it close.

**Limits.**
- Needs no secret: the default `GITHUB_TOKEN` with `issues: write`.
- In public repos GitHub disables scheduled workflows after 60 days without repository activity; an agent
  that commits regularly keeps it alive. Scheduled runs can start late when Actions is under load.
- `--command` runs with `shell=True`: only put your own commands there, never text from issues or PRs.
- `--command` output goes into the issue. In a public repo the issue is public: do not run commands that
  print secrets, paths you consider private, or `@name` mentions.
- `--stale` sees only the fetched history (`fetch-depth: 200` in the workflow); a file last changed more than
  200 commits ago reads as "no commit touches this file". Raise the depth if your agent commits a lot.
- It tells you something is wrong, not how to fix it.
