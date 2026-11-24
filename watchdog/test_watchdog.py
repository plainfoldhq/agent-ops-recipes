"""Offline tests for watchdog_checks.py. Run: python3 -m unittest test_watchdog.py"""
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import watchdog_checks as wd  # noqa: E402


@unittest.skipUnless(shutil.which("git"), "git not installed")
class Watchdog(unittest.TestCase):
    def setUp(self):
        self.repo = tempfile.mkdtemp()
        self.git("init", "-q")
        self.commit("STATE.md", "x\n", hours_ago=40)
        self.commit("fresh.md", "y\n", hours_ago=2)

    def tearDown(self):
        shutil.rmtree(self.repo)

    def git(self, *args, env=None):
        subprocess.run(["git", *args], cwd=self.repo, check=True, capture_output=True,
                       env={**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
                            "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com", **(env or {})})

    def commit(self, name, text, hours_ago):
        with open(os.path.join(self.repo, name), "w") as f:
            f.write(text)
        stamp = f"@{int(time.time() - hours_ago * 3600)} +0000"
        self.git("add", name)
        self.git("commit", "-qm", name, env={"GIT_AUTHOR_DATE": stamp, "GIT_COMMITTER_DATE": stamp})

    def write_json(self, name, obj):
        with open(os.path.join(self.repo, name), "w") as f:
            json.dump(obj, f)

    def problems(self, argv):
        wd.main(argv + ["--out", "problems.md"], repo=self.repo, out=lambda *_: None)
        return pathlib.Path(os.path.join(self.repo, "problems.md")).read_text()

    def test_healthy_writes_empty_file(self):
        self.write_json("usage.json", {"weekly_pct": 12, "error": None})
        p = self.problems(["--stale", "fresh.md:30", "--json-field", "usage.json:weekly_pct",
                           "--command", "ok=true"])
        self.assertEqual(p, "")

    def test_stale_file(self):
        p = self.problems(["--stale", "STATE.md:30"])
        self.assertIn("STATE.md last changed 40 h ago", p)

    def test_never_committed(self):
        self.assertIn("no commit touches", self.problems(["--stale", "missing.md:30"]))

    def test_json_error_null_and_unreadable(self):
        self.write_json("a.json", {"weekly_pct": 5, "error": "401 auth"})
        self.write_json("b.json", {"weekly_pct": None})
        p = self.problems(["--json-field", "a.json:weekly_pct", "--json-field", "b.json:weekly_pct",
                           "--json-field", "nope.json:x"])
        self.assertIn("a.json: error = 401 auth", p)
        self.assertIn("b.json: weekly_pct is missing or null", p)
        self.assertIn("nope.json: cannot read", p)

    def test_command_failure_tail(self):
        p = self.problems(["--command", "audit=echo FAIL something; exit 3"])
        self.assertIn("audit: exit 3", p)
        self.assertIn("FAIL something", p)

    def test_bad_spec(self):
        with self.assertRaises(SystemExit):
            wd.main(["--stale", "STATE.md"], repo=self.repo)
        with self.assertRaises(SystemExit):
            wd.main(["--command", "no-equals-sign"], repo=self.repo)

    def test_workflow_uses_problems_file(self):
        y = pathlib.Path(os.path.join(HERE, "watchdog.yml")).read_text()
        self.assertIn("-s problems.md", y)
        self.assertIn("issues: write", y)
        self.assertIn("select(.title == env.TITLE)", y)  # exact title match
        self.assertNotIn("secrets.", y)  # needs only the default token


if __name__ == "__main__":
    unittest.main()
