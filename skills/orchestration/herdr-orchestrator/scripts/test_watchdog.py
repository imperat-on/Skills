#!/usr/bin/env python3
"""Watchdog tests: deterministic, temp repos only, fake Herdr on PATH, no live runtime.

Run:  python3 scripts/test_watchdog.py -v

Covers: the signal combination (agent state, output, process liveness, pane/workspace/worktree
existence, timestamps), stall detection with configurable conservative thresholds, blocked
classification, agent/process death, early scope-violation detection, degraded operation without a
reachable runtime, event emission, and the guarantee that observation never mutates the repository.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
WATCH = HERE / "watchdog.py"
ORCH = HERE / "orch.py"
PY = sys.executable or "python3"

FAKE_HERDR_SRC = '''#!/usr/bin/env python3
"""Fake herdr: answers the read-only subcommands the watchdog uses, from <self>.json."""
import json
import sys

cfg = json.loads(open(sys.argv[0] + ".json").read())
args = sys.argv[1:]


def emit(obj):
    print(json.dumps(obj))


if args[:2] == ["agent", "list"]:
    emit({"result": {"type": "agent_list", "agents": cfg.get("agents", [])}})
elif args[:2] == ["pane", "list"]:
    emit({"result": {"panes": [{"pane_id": p} for p in cfg.get("panes", [])]}})
elif args[:2] == ["workspace", "list"]:
    emit({"result": {"workspaces": [{"workspace_id": w} for w in cfg.get("workspaces", [])]}})
elif args[:2] == ["agent", "read"]:
    print(cfg.get("output", {}).get(args[2], "unchanged output"))
elif args[:2] == ["pane", "process-info"]:
    pane = args[args.index("--pane") + 1] if "--pane" in args else ""
    emit({"result": {"foreground_processes": cfg.get("process_info", {}).get(pane, [])}})
else:
    emit({"result": {}})
'''


def run(args, cwd=None, env=None):
    return subprocess.run([PY, str(WATCH), *args], cwd=cwd, capture_output=True, text=True,
                          timeout=180, env=env)


class WatchdogTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="watchdog-test-")
        base = Path(self._tmp.name)
        self.root = base / "repo"
        self.root.mkdir(parents=True)
        self.bin = base / "bin"
        self.bin.mkdir()
        self.wt = base / "wt-a"
        self.set_runtime()
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.name", "wd-test")
        self.git("config", "user.email", "wd@localhost")
        (self.root / "README.md").write_text("test repo\n", encoding="utf-8")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "init")
        self.orch("init", "--run-id", "t-1")
        self.orch("add-task", "--id", "a", "--title", "task a", "--acceptance",
                  "observable outcome", "--scope", "src/app")
        self.git("worktree", "add", "-q", "-b", "agent/t-1/a", str(self.wt))
        self._write(self.wt / "src/app/main.py", "print('x')\n")
        self.git("add", "-A", cwd=self.wt)
        self.git("commit", "-q", "-m", "work", cwd=self.wt)
        self.commit = self.git("rev-parse", "HEAD", cwd=self.wt).stdout.strip()
        self.orch("contract", "--id", "a", "--role", "worker", "--objective",
                  "do the thing properly", "--write-scope", "src/app/**", "--forbidden-scope",
                  "backend/**", "--acceptance", "it works", "--required-check", "unit tests",
                  "--worktree", str(self.wt), "--branch", "agent/t-1/a")
        self.orch("set-task", "--id", "a", "--status", "working", "--agent", "w_a", "--pane",
                  "w9:p1", "--workspace", "w9", "--worktree", str(self.wt), "--branch",
                  "agent/t-1/a", "--launch-mode", "autonomous", "--launch-kind", "opencode",
                  "--launch-verified", "1")

    def tearDown(self):
        self._tmp.cleanup()

    # ------------------------------------------------------------------ plumbing
    def git(self, *args, cwd=None):
        return subprocess.run(["git", *args], cwd=str(cwd or self.root), capture_output=True,
                              text=True, timeout=60)

    def orch(self, *args):
        return subprocess.run([PY, str(ORCH), "--repo-root", str(self.root), *args],
                              capture_output=True, text=True, timeout=120)

    @staticmethod
    def _write(path: Path, text: str):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def set_runtime(self, *, agents=None, panes=("w9:p1",), workspaces=("w9",),
                    process_info=None, output=None):
        self._write(self.bin / "herdr", FAKE_HERDR_SRC)
        os.chmod(self.bin / "herdr", 0o755)
        live = agents
        if live is None:
            live = [{"name": "w_a", "agent": "opencode", "agent_status": "working",
                     "pane_id": "w9:p1", "workspace_id": "w9", "cwd": str(self.wt)}]
        cfg = {"agents": live, "panes": list(panes), "workspaces": list(workspaces),
               "process_info": process_info or {},
               "output": output or {}}
        self._write(self.bin / "herdr.json", json.dumps(cfg))

    def env(self):
        return {**os.environ, "PATH": f"{self.bin}:{os.environ['PATH']}"}

    def sample(self, *extra, herdr=True, persist=True):
        args = ["--repo-root", str(self.root), *extra]
        if not herdr:
            args.append("--no-herdr")
        return run(args, env=self.env())

    def report(self, *extra, **kw):
        r = self.sample(*extra, **kw)
        payload = None
        try:
            payload = json.loads(r.stdout)
        except ValueError:
            payload = None
        return r, payload

    def task_row(self, payload, tid="a"):
        return next(row for row in payload["tasks"] if row["task_id"] == tid)

    def events(self):
        path = self.root / ".orchestrator" / "events.jsonl"
        return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]

    def age_worktree(self, when: float):
        for base, dirs, files in os.walk(self.wt):
            if ".git" in dirs:
                dirs.remove(".git")
            for name in files:
                os.utime(Path(base) / name, (when, when))
        os.utime(self.wt, (when, when))

    def age_last_commit(self, when: float):
        stamp = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(when))
        env = {**os.environ, "GIT_COMMITTER_DATE": stamp, "GIT_AUTHOR_DATE": stamp}
        subprocess.run(["git", "commit", "--amend", "--no-edit", "--date", stamp], cwd=str(self.wt),
                       env=env, capture_output=True, text=True, timeout=60, check=True)
        self.commit = self.git("rev-parse", "HEAD", cwd=self.wt).stdout.strip()

    # ------------------------------------------------------------------ tests
    def test_healthy_working_agent(self):
        r, payload = self.report("--json")
        row = self.task_row(payload)
        self.assertIn(row["classification"], ("healthy", "working"))
        self.assertTrue(payload["herdr"]["available"])
        self.assertEqual(payload["verdict"], "healthy")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue((self.root / ".orchestrator" / "watchdog" / "last_sample.json").is_file())

    def test_required_checkpoint_missing_is_flagged(self):
        """checkpoint_policy=required and nothing on disk: a worker killed now forces reconstruction
        from Git alone, so the orchestrator has to be told (drill finding: two workers ignored the
        instruction and nothing noticed)."""
        self.orch("contract", "--id", "a", "--checkpoint-policy", "required")
        # past checkpoint_after (600) but under stall_after (900): no write and no commit for 700s
        self.age_worktree(time.time() - 700)
        self.age_last_commit(time.time() - 700)
        r, payload = self.report("--json")
        row = self.task_row(payload)
        self.assertEqual(row["classification"], "checkpoint_missing")
        self.assertIn("reconstruct", row["why"])
        self.assertEqual(payload["verdict"], "attention")

    def test_required_checkpoint_present_is_not_flagged(self):
        self.orch("contract", "--id", "a", "--checkpoint-policy", "required")
        ck = self.root / ".orchestrator" / "checkpoints" / "a.json"
        ck.parent.mkdir(parents=True, exist_ok=True)
        ck.write_text(json.dumps({"task_id": "a", "phase": 1, "current": "implementando",
                                  "last_known_commit": self.commit}), encoding="utf-8")
        self.age_worktree(time.time() - 700)
        self.age_last_commit(time.time() - 700)
        r, payload = self.report("--json")
        self.assertNotEqual(self.task_row(payload)["classification"], "checkpoint_missing")

    def test_agent_gone_is_failed_and_needs_attention(self):
        self.set_runtime(agents=[])
        r, payload = self.report("--json")
        row = self.task_row(payload)
        self.assertEqual(row["classification"], "agent_gone")
        self.assertIn("herdr agent list", row["why"])
        self.assertEqual(payload["verdict"], "attention")
        self.assertEqual(r.returncode, 1)
        self.assertIn("worker_failed", [e["event"] for e in self.events()])

    def test_blocked_is_a_decision_point_not_completion(self):
        self.set_runtime(agents=[{"name": "w_a", "agent": "opencode", "agent_status": "blocked",
                                  "pane_id": "w9:p1", "workspace_id": "w9"}])
        r, payload = self.report("--json")
        row = self.task_row(payload)
        self.assertEqual(row["classification"], "blocked")
        self.assertIn("decision point", row["why"])
        self.assertEqual(r.returncode, 1)
        events = [e["event"] for e in self.events()]
        self.assertIn("worker_blocked", events)
        self.assertNotIn("worker_idle", events)

    def test_process_dead_when_the_pane_runs_another_process(self):
        self.set_runtime(process_info={"w9:p1": [{"argv": ["bash"]}]})
        r, payload = self.report("--json")
        row = self.task_row(payload)
        self.assertEqual(row["classification"], "process_dead")
        self.assertFalse(row["signals"]["process_matches_kind"])
        self.assertEqual(r.returncode, 1)

    def test_pane_missing(self):
        self.set_runtime(panes=("w9:p2",))
        r, payload = self.report("--json")
        self.assertEqual(self.task_row(payload)["classification"], "pane_missing")
        self.assertEqual(r.returncode, 1)

    def test_workspace_missing(self):
        self.set_runtime(workspaces=("w1",))
        r, payload = self.report("--json")
        self.assertEqual(self.task_row(payload)["classification"], "workspace_missing")

    def test_worktree_missing(self):
        shutil.rmtree(self.wt)
        r, payload = self.report("--json")
        row = self.task_row(payload)
        self.assertEqual(row["classification"], "worktree_missing")
        self.assertIn("recorded worktree path does not exist", row["why"])
        self.assertEqual(r.returncode, 1)

    def test_stall_requires_a_second_sample_and_combined_signals(self):
        # first sample: fresh activity -> not stalled
        first, payload = self.report("--json")
        self.assertIn(self.task_row(payload)["classification"], ("healthy", "working"))
        # activity stops: old commit + old file mtimes, agent still claims to be working
        old = time.time() - 4000
        self.age_last_commit(old)
        self.age_worktree(old)
        second, payload2 = self.report("--json", "--stall-after", "900")
        row = self.task_row(payload2)
        self.assertEqual(row["classification"], "stalled")
        self.assertGreater(row["seconds_since_activity"], 900)
        self.assertIn("no commit/checkpoint/output change", row["why"])
        self.assertEqual(second.returncode, 1)
        self.assertIn("worker_stalled", [e["event"] for e in self.events()])
        # the watchdog only observed: it never killed or moved anything
        self.assertEqual(self.git("rev-parse", "HEAD", cwd=self.wt).stdout.strip(), self.commit)

    def test_thresholds_are_conservative_and_configurable(self):
        old = time.time() - 4000
        self.age_last_commit(old)
        self.age_worktree(old)
        self.report("--json", persist=False)                   # warm the previous sample
        r, payload = self.report("--json", "--stall-after", "100000", persist=False)
        row = self.task_row(payload)
        self.assertNotEqual(row["classification"], "stalled")
        self.assertLess(row["seconds_since_activity"], 100000)

    def test_scope_violation_detected_before_it_is_committed(self):
        self._write(self.wt / "backend/auth.ts", "export const x = 1\n")
        self._write(self.wt / "docs/notes.md", "scratch\n")
        r, payload = self.report("--json")
        row = self.task_row(payload)
        self.assertEqual(row["classification"], "scope_violation")
        kinds = {v["path"]: v["kind"] for v in row["scope_violation"]}
        self.assertEqual(kinds["backend/auth.ts"], "forbidden")       # inside forbidden_scope
        self.assertEqual(kinds["docs/notes.md"], "unexpected")        # outside write_scope
        self.assertEqual(r.returncode, 1)
        self.assertEqual([e["event"] for e in self.events()].count("scope_violation"), 2)
        # early detection: the offending paths are still uncommitted
        self.assertEqual(self.git("log", "-1", "--format=%H", cwd=self.wt).stdout.strip(),
                         self.commit)

    def test_observation_does_not_mutate_the_repository(self):
        before_head = self.git("rev-parse", "HEAD").stdout.strip()
        before_status = self.git("status", "--porcelain").stdout
        self.sample("--json")
        self.assertEqual(self.git("rev-parse", "HEAD").stdout.strip(), before_head)
        self.assertEqual(self.git("status", "--porcelain").stdout, before_status)

    def test_degraded_without_a_reachable_runtime(self):
        r, payload = self.report("--json", herdr=False)
        self.assertFalse(payload["herdr"]["available"])
        self.assertEqual(payload["verdict"], "degraded")
        self.assertIn("UNAVAILABLE", r.stdout) if not r.stdout.startswith("{") else None
        self.assertEqual(r.returncode, 1)
        self.assertIn("watchdog_degraded", [e["event"] for e in self.events()])

    def test_fixture_snapshot_is_accepted_without_a_live_runtime(self):
        fixture = self.root.parent / "fixture.json"
        fixture.write_text(json.dumps({
            "agents": [{"name": "w_a", "agent": "opencode", "agent_status": "idle",
                        "pane_id": "w9:p1", "workspace_id": "w9"}],
            "panes": ["w9:p1"], "workspaces": ["w9"],
            "process_info": {"w9:p1": [{"argv": ["opencode", "--auto"]}]},
        }), encoding="utf-8")
        r, payload = self.report("--json", "--fixture", str(fixture), persist=False)
        row = self.task_row(payload)
        self.assertEqual(row["classification"], "idle")       # idle + no commit -> inspect
        self.assertEqual(payload["herdr"]["source"], f"fixture:{fixture}")

    def test_watch_loop_runs_a_bounded_number_of_samples(self):
        r = self.sample("--watch", "--interval", "5", "--iterations", "1", "--no-persist")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("WATCHDOG  verdict=", r.stdout)
        self.assertIn("observation only", r.stdout)

    def test_no_state_at_all_is_not_a_crash(self):
        shutil.rmtree(self.root / ".orchestrator")
        r, payload = self.report("--json", "--no-persist")
        self.assertEqual(payload["tasks"], [])
        self.assertIsNone(payload["run_id"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
