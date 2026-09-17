#!/usr/bin/env python3
"""Test suite for scripts/orch.py (stdlib unittest, no network, temp dirs only).

Run:  python3 scripts/test_orch.py -v
Covers: run configuration (three axes), constraints, launch records, persistence/recovery of the
configuration, legacy-state migration, validation, reporting and the skill-proposal path.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ORCH = HERE / "orch.py"
SKILL_DIR = HERE.parent
PY = sys.executable or "python3"
sys.path.insert(0, str(HERE))

import contracts  # noqa: E402  (same directory: the contract/gate logic under test)


def run(args, cwd=None):
    return subprocess.run([PY, str(ORCH), *args], cwd=cwd, capture_output=True, text=True, timeout=120)


def git(args, cwd):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, timeout=120)


class OrchTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="orch-test-")
        self.root = Path(self._tmp.name) / "repo"
        self.root.mkdir(parents=True)
        git(["init", "-q", "-b", "main"], self.root)
        git(["config", "user.name", "orch-test"], self.root)
        git(["config", "user.email", "orch-test@localhost"], self.root)
        (self.root / "README.md").write_text("test repo\n", encoding="utf-8")
        git(["add", "-A"], self.root)
        git(["commit", "-q", "-m", "init"], self.root)

    def tearDown(self):
        self._tmp.cleanup()

    def init(self, *extra):
        r = run(["--repo-root", str(self.root), "init", "--run-id", "t-1", *extra])
        self.assertEqual(r.returncode, 0, r.stderr)
        return r

    def state(self):
        return json.loads((self.root / ".orchestrator" / "state.json").read_text(encoding="utf-8"))

    def add_task(self, tid="a", **kw):
        args = ["--repo-root", str(self.root), "add-task", "--id", tid, "--title", f"task {tid}",
                "--acceptance", "observable outcome"]
        for k, v in kw.items():
            args += [f"--{k.replace('_', '-')}", str(v)]
        r = run(args)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r

    # ------------------------------------------------------------------ helpers (v1.2)
    def orch(self, *args):
        return run(["--repo-root", str(self.root), *args])

    def gitc(self, *args, cwd=None):
        r = git(list(args), cwd or self.root)
        if r.returncode != 0:
            raise AssertionError(f"git {' '.join(args)} failed: {r.stderr}")
        return r.stdout.strip()

    def commit_files(self, cwd, files: dict, message="work"):
        for rel, content in files.items():
            path = Path(cwd) / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        git(["add", "-A"], cwd)
        r = git(["commit", "-q", "-m", message], cwd)
        self.assertEqual(r.returncode, 0, r.stderr)
        return self.gitc("rev-parse", "HEAD", cwd=cwd)

    def make_worktree(self, tid="a", files=None, branch=None):
        wt = self.root.parent / f"wt-{tid}"
        branch = branch or f"agent/t-1/{tid}"
        self.gitc("worktree", "add", "-q", "-b", branch, str(wt))
        commit = self.commit_files(wt, files or {"src/app/main.py": "print('x')\n"})
        return wt, branch, commit

    def make_contract(self, tid="a", *, role="worker", objective="Implement the navigation fix",
                      write_scope=("src/app/**",), forbidden=("backend/**", "database/**"),
                      acceptance=("navigation works",), checks=("unit tests",),
                      extra=(), expect_ok=True, **flags):
        args = ["contract", "--id", tid, "--role", role]
        for flag, values in (("--objective", (objective,) if isinstance(objective, str) else objective),
                             ("--write-scope", write_scope), ("--forbidden-scope", forbidden),
                             ("--acceptance", acceptance), ("--required-check", checks),
                             ("--read-scope", ("**",))):
            for v in values:
                args += [flag, v]
        for flag, value in flags.items():
            args += [f"--{flag.replace('_', '-')}", str(value)]
        args += list(extra)
        r = self.orch(*args)
        if expect_ok:
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r

    def task_json(self, tid="a"):
        data = json.loads((self.root / ".orchestrator" / "tasks.json").read_text(encoding="utf-8"))
        return next(t for t in data["tasks"] if t["id"] == tid)

    def events(self):
        path = self.root / ".orchestrator" / "events.jsonl"
        return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]

    def prepare_task(self, tid="a", *, files=None, **contract_kw):
        """A realistic mutating task: graph entry + worktree + branch + valid contract + dispatch."""
        self.add_task(tid, mutates=1, scope="src/app")
        wt, branch, commit = self.make_worktree(tid, files)
        self.make_contract(tid, worktree=str(wt), branch=branch, **contract_kw)
        self.orch("set-task", "--id", tid, "--status", "working", "--agent", f"w_{tid}",
                  "--pane", "w9:p1", "--workspace", "w9", "--worktree", str(wt),
                  "--branch", branch, "--launch-mode", "autonomous", "--launch-kind", "opencode",
                  "--launch-arg=--auto", "--launch-verified", "1")
        return wt, branch, commit

    def close_gate(self, tid="a", *, tests="pass", verdict="PASS", collect_result=True):
        """A realistic end of the worker→review→gate chain: verify, collect the result, record checks."""
        commit = self.task_json(tid).get("commit")
        if not commit:
            self.orch("verify", "--id", tid)          # records the real commit + scope from git
            commit = self.task_json(tid).get("commit") or ""
        if collect_result:
            report = (f"result: DONE\ntask_id: {tid}\ncommit: {commit}\n"
                      f"changed_files: [src/app/main.py]\ntests:\n  - command: pytest -q\n"
                      f"    exit_code: 0\n    result: pass\nscope_violations: []\n"
                      f"blockers: []\nnotes: []\n")
            r = self.orch("result", "--id", tid, "--text", report)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return self.orch("set-task", "--id", tid, "--tests-status", tests,
                         "--tests-command", "pytest -q", "--tests-evidence",
                         str(self.root / ".orchestrator" / "reports" / f"{tid}-tests.txt"),
                         "--verdict", verdict)


class TestInit(OrchTestCase):
    def test_defaults_are_supervised_semi_auto_autonomous(self):
        self.init()
        s = self.state()
        self.assertEqual(s["coordination_mode"], "supervised_auto")
        self.assertEqual(s["team_mode"], "semi_auto")
        self.assertEqual(s["worker_execution_mode"], "autonomous")
        self.assertEqual(s["team_constraints"]["allowed_agent_kinds"], [])
        self.assertEqual(s["team_constraints"]["pinned_roles"], {})
        self.assertIsNone(s["team_constraints"]["max_workers"])
        self.assertEqual(s["version"], 3)
        self.assertEqual(s["watchdog"]["stall_after"], 900)

    def test_explicit_modes_and_constraints(self):
        self.init("--coordination-mode", "auto", "--team-mode", "manual",
                  "--worker-execution-mode", "autonomous",
                  "--allowed-agent-kind", "opencode", "--allowed-agent-kind", "opencode",
                  "--pin", "worker=opencode", "--max-workers", "2",
                  "--constraint-note", "user pinned the team")
        s = self.state()
        self.assertEqual(s["coordination_mode"], "auto")
        self.assertEqual(s["team_mode"], "manual")
        # deduplicated, order-stable
        self.assertEqual(s["team_constraints"]["allowed_agent_kinds"], ["opencode"])
        self.assertEqual(s["team_constraints"]["pinned_roles"], {"worker": "opencode"})
        self.assertEqual(s["team_constraints"]["max_workers"], 2)
        self.assertEqual(len(s["team_constraints"]["notes"]), 1)

    def test_invalid_mode_rejected(self):
        r = run(["--repo-root", str(self.root), "init", "--coordination-mode", "yolo"])
        self.assertEqual(r.returncode, 2)
        self.assertIn("invalid choice", r.stderr)

    def test_orchestrator_dir_excluded_from_git(self):
        self.init()
        exclude = (self.root / ".git" / "info" / "exclude").read_text(encoding="utf-8")
        self.assertIn(".orchestrator/", exclude)
        self.assertFalse((self.root / ".gitignore").exists())
        self.assertEqual(git(["status", "--porcelain"], self.root).stdout.strip(), "")

    def test_second_init_requires_force(self):
        self.init()
        r = run(["--repo-root", str(self.root), "init"])
        self.assertEqual(r.returncode, 2)
        self.assertIn("already exists", r.stderr)


class TestSetModes(OrchTestCase):
    def test_change_logs_event_and_decision(self):
        self.init()
        r = run(["--repo-root", str(self.root), "set-modes", "--coordination-mode", "assisted",
                 "--team-mode", "manual", "--allowed-agent-kind", "opencode",
                 "--pin", "reviewer=opencode", "--note", "user asked for approvals"])
        self.assertEqual(r.returncode, 0, r.stderr)
        s = self.state()
        self.assertEqual(s["coordination_mode"], "assisted")
        self.assertEqual(s["team_mode"], "manual")
        self.assertEqual(s["worker_execution_mode"], "autonomous")  # untouched
        events = [json.loads(l) for l in
                  (self.root / ".orchestrator" / "events.jsonl").read_text(encoding="utf-8").splitlines()]
        self.assertIn("mode_changed", [e["event"] for e in events])
        mode_event = [e for e in events if e["event"] == "mode_changed"][-1]
        self.assertEqual(mode_event["coordination_mode"], "assisted")
        decisions = (self.root / ".orchestrator" / "decisions.md").read_text(encoding="utf-8")
        self.assertIn("user asked for approvals", decisions)

    def test_unpin_and_clear_kinds(self):
        self.init("--pin", "worker=opencode")
        r = run(["--repo-root", str(self.root), "set-modes", "--unpin", "worker",
                 "--clear-allowed-kinds"])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.state()["team_constraints"]["pinned_roles"], {})

    def test_nothing_to_change_fails(self):
        self.init()
        r = run(["--repo-root", str(self.root), "set-modes"])
        self.assertEqual(r.returncode, 2)
        self.assertIn("nothing to change", r.stderr)

    def test_modes_output_json(self):
        self.init("--allowed-agent-kind", "opencode")
        r = run(["--repo-root", str(self.root), "modes", "--json"])
        self.assertEqual(r.returncode, 0, r.stderr)
        payload = json.loads(r.stdout)
        self.assertEqual(payload["team_constraints"]["allowed_agent_kinds"], ["opencode"])


class TestPersistenceAndRecovery(OrchTestCase):
    def test_configuration_survives_a_fresh_process(self):
        self.init("--coordination-mode", "assisted", "--team-mode", "manual",
                  "--worker-execution-mode", "interactive", "--allowed-agent-kind", "opencode")
        # a brand-new process, as a recovered session would be
        r = run(["--repo-root", str(self.root), "status", "--json"])
        self.assertEqual(r.returncode, 0, r.stderr)
        st = json.loads(r.stdout)["state"]
        self.assertEqual(st["coordination_mode"], "assisted")
        self.assertEqual(st["team_mode"], "manual")
        self.assertEqual(st["worker_execution_mode"], "interactive")
        self.assertEqual(st["team_constraints"]["allowed_agent_kinds"], ["opencode"])

    def test_legacy_state_is_migrated_to_defaults_with_a_warning(self):
        self.init()
        path = self.root / ".orchestrator" / "state.json"
        s = json.loads(path.read_text(encoding="utf-8"))
        for key in ("coordination_mode", "team_mode", "worker_execution_mode", "team_constraints"):
            s.pop(key, None)
        s["version"] = 1
        path.write_text(json.dumps(s, indent=2), encoding="utf-8")
        r = run(["--repo-root", str(self.root), "validate", "--no-herdr"])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("legacy state.json", r.stdout)
        r2 = run(["--repo-root", str(self.root), "modes", "--json"])
        self.assertEqual(json.loads(r2.stdout)["coordination_mode"], "supervised_auto")
        # a write persists the normalized values
        run(["--repo-root", str(self.root), "set-modes", "--team-mode", "semi_auto"])
        self.assertIn("coordination_mode", json.loads(path.read_text(encoding="utf-8")))

    def test_no_temp_files_left_behind(self):
        self.init()
        self.add_task("a")
        run(["--repo-root", str(self.root), "set-modes", "--team-mode", "auto"])
        leftovers = list((self.root / ".orchestrator").glob(".tmp-*"))
        self.assertEqual(leftovers, [])


class TestTasksAndLaunch(OrchTestCase):
    def test_launch_record_round_trip(self):
        self.init()
        self.add_task("a")
        r = run(["--repo-root", str(self.root), "set-task", "--id", "a", "--status", "working",
                 "--agent", "w_a", "--pane", "w9:p1", "--workspace", "w9",
                 "--worktree", str(self.root / "wt-a"), "--branch", "agent/t/a",
                 "--launch-mode", "autonomous", "--launch-kind", "opencode",
                 "--launch-arg=--auto", "--launch-verified", "1"])
        self.assertEqual(r.returncode, 0, r.stderr)
        t = json.loads((self.root / ".orchestrator" / "tasks.json").read_text(encoding="utf-8"))["tasks"][0]
        self.assertEqual(t["worker_execution"]["mode"], "autonomous")
        self.assertEqual(t["worker_execution"]["kind"], "opencode")
        self.assertEqual(t["worker_execution"]["args"], ["--auto"])
        self.assertTrue(t["worker_execution"]["verified_after_spawn"])
        s = self.state()
        self.assertIn("w_a", s["resources"]["owned_agents"])
        self.assertIn("agent/t/a", s["resources"]["owned_branches"])

    def test_invalid_launch_mode_rejected(self):
        self.init()
        self.add_task("a")
        r = run(["--repo-root", str(self.root), "set-task", "--id", "a", "--launch-mode", "yolo"])
        self.assertEqual(r.returncode, 2)

    def test_validate_flags_missing_acceptance_and_worktree(self):
        self.init()
        self.add_task("a", mutates=0)
        r = run(["--repo-root", str(self.root), "validate", "--no-herdr"])
        self.assertEqual(r.returncode, 0, r.stdout)
        tasks_path = self.root / ".orchestrator" / "tasks.json"
        data = json.loads(tasks_path.read_text(encoding="utf-8"))
        data["tasks"][0]["acceptance"] = []
        tasks_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        r = run(["--repo-root", str(self.root), "validate", "--no-herdr"])
        self.assertEqual(r.returncode, 1)
        self.assertIn("no acceptance criteria", r.stdout)

    def test_ready_respects_dependencies(self):
        self.init()
        self.add_task("a")
        self.add_task("b", depends_on="a")
        r = run(["--repo-root", str(self.root), "ready"])
        self.assertIn("a\t", r.stdout)
        self.assertNotIn("b\t", r.stdout)


class TestProposalsAndReport(OrchTestCase):
    def test_propose_records_candidate_without_touching_the_skill(self):
        self.init()
        skill_md = SKILL_DIR / "SKILL.md"
        before = hashlib.sha256(skill_md.read_bytes()).hexdigest()
        r = run(["--repo-root", str(self.root), "propose", "--kind", "pitfall",
                 "--title", "reviewer parked at a permission dialog",
                 "--detail", "use an isolated clone inside the reviewer cwd"])
        self.assertEqual(r.returncode, 0, r.stderr)
        after = hashlib.sha256(skill_md.read_bytes()).hexdigest()
        self.assertEqual(before, after, "recording a proposal must not edit the skill")
        props = (self.root / ".orchestrator" / "skill-proposals.md").read_text(encoding="utf-8")
        self.assertIn("## [proposed] reviewer parked at a permission dialog", props)
        self.assertIn("kind: pitfall", props)
        events = [json.loads(l) for l in
                  (self.root / ".orchestrator" / "events.jsonl").read_text(encoding="utf-8").splitlines()]
        self.assertIn("skill_proposal_recorded", [e["event"] for e in events])

    def test_propose_rejects_unknown_kind(self):
        self.init()
        r = run(["--repo-root", str(self.root), "propose", "--kind", "nonsense", "--title", "x"])
        self.assertEqual(r.returncode, 2)

    def test_report_shows_configuration_launch_and_proposal_count(self):
        self.init("--coordination-mode", "auto", "--team-mode", "manual",
                  "--allowed-agent-kind", "opencode")
        wt, branch, commit = self.prepare_task("a")
        self.close_gate("a")
        r = self.orch("merge-gate", "--id", "a", "--live")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        r = self.orch("set-task", "--id", "a", "--status", "integrated", "--commit", commit)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.orch("propose", "--kind", "improvement", "--title", "x")
        r = self.orch("report", "--result", "success", "--out", str(self.root / "r.txt"))
        self.assertEqual(r.returncode, 0, r.stderr)
        text = (self.root / "r.txt").read_text(encoding="utf-8")
        self.assertIn("RESULT: SUCCESS", text)
        self.assertIn("- coordination_mode: auto", text)
        self.assertIn("- team_mode: manual", text)
        self.assertIn("- allowed_agent_kinds: ['opencode']", text)
        self.assertIn("launch=opencode --auto verified=True", text)
        self.assertIn("Skill proposals recorded: 1", text)
        self.assertIn("the skill was NOT modified", text)
        # v1.2 sections
        self.assertIn("Contracts and scope:", text)
        self.assertIn("Merge gates:", text)
        self.assertIn("ready=True", text)
        self.assertIn("contract=pass", text)


class TestTaskContracts(OrchTestCase):
    """TASK CONTRACTS: structured, persisted, validated before delegation (v1.2)."""

    def test_valid_contract_is_persisted_and_rendered_for_the_worker(self):
        self.init()
        self.add_task("a", mutates=1, scope="src/app")
        wt, branch, commit = self.make_worktree("a")
        r = self.make_contract("a", worktree=str(wt), branch=branch, base_commit=commit,
                               objective="Implement controller navigation in Big Picture",
                               write_scope=("src/app/**", "src/components/controller/**"),
                               forbidden=("backend/**", "database/**", "infra/**"),
                               acceptance=("controller navigation works",
                                           "keyboard navigation remains functional",
                                           "existing tests remain green"),
                               checks=("relevant unit tests", "typecheck"),
                               extra=("--deliverable", "focused commit"))
        self.assertIn("TASK_CONTRACT: VALID", r.stdout)
        self.assertIn("write_scope:", r.stdout)
        self.assertIn("src/components/controller/**", r.stdout)
        contract = json.loads((self.root / ".orchestrator" / "contracts" / "a.json")
                              .read_text(encoding="utf-8"))
        self.assertEqual(contract["write_scope"],
                         ["src/app/**", "src/components/controller/**"])
        self.assertEqual(contract["forbidden_scope"], ["backend/**", "database/**", "infra/**"])
        self.assertEqual(contract["mutation_policy"], "worktree_only")
        self.assertEqual(contract["base_commit"], commit)
        self.assertEqual(contract["role"], "worker")
        self.assertIn("report the blocked reason", contract["when_blocked"])
        self.assertEqual(contract["deliverables"], ["focused commit"])
        self.assertEqual(len(contract["acceptance_criteria"]), 3)
        self.assertEqual(contract["contract_version"], 1)
        task = self.task_json("a")
        self.assertEqual(len(task["contract_digest"]), 16)
        self.assertEqual(task["expected_scope"], contract["write_scope"])
        self.assertIn("contract_written", [e["event"] for e in self.events()])

    def test_invalid_contract_is_refused_and_blocks_ready(self):
        self.init()
        self.add_task("a", mutates=1, scope="src/app")
        r = self.make_contract("a", write_scope=(), expect_ok=False)
        self.assertEqual(r.returncode, 1)
        self.assertIn("TASK_CONTRACT_INVALID", r.stdout)
        self.assertIn("write_scope", r.stdout)
        r = self.orch("set-task", "--id", "a", "--status", "ready")
        self.assertEqual(r.returncode, 2)
        self.assertIn("TASK_CONTRACT_INVALID", r.stderr)
        r = self.orch("ready")
        self.assertNotIn("a\tworker", r.stdout)
        self.assertIn("TASK_CONTRACT_INVALID", r.stdout)
        self.assertIn("contract_invalid", [e["event"] for e in self.events()])

    def test_broad_write_scope_needs_an_explicit_justification(self):
        self.init()
        self.add_task("a", mutates=1)
        r = self.make_contract("a", write_scope=("**",), expect_ok=False)
        self.assertEqual(r.returncode, 1)
        self.assertIn("catch-all", r.stdout)
        r = self.make_contract("a", write_scope=("**",), extra=("--force",),
                               scope_justification="repo-wide rename authorised by the user")
        self.assertIn("TASK_CONTRACT: VALID", r.stdout)

    def test_read_only_task_contract_needs_no_write_scope(self):
        self.init()
        self.add_task("r", mutates=0, acceptance="findings reported")
        r = self.make_contract("r", role="researcher", write_scope=(),
                               acceptance=("findings reported",))
        self.assertIn("TASK_CONTRACT: VALID", r.stdout)
        task = self.task_json("r")
        self.assertFalse(task["mutates_files"])
        self.assertEqual(task["contract"]["mutation_policy"], "read_only")

    def test_material_contract_change_must_pass_through_the_orchestrator(self):
        self.init()
        self.add_task("a", mutates=1)
        self.make_contract("a")
        before = self.task_json("a")["contract_digest"]
        r = self.make_contract("a", write_scope=("src/other/**",), expect_ok=False)
        self.assertEqual(r.returncode, 2)
        self.assertIn("material change", r.stderr)
        self.assertEqual(self.task_json("a")["contract_digest"], before)
        self.make_contract("a", write_scope=("src/other/**",), extra=("--force",))
        self.assertNotEqual(self.task_json("a")["contract_digest"], before)

    def test_yaml_contract_file_is_accepted(self):
        self.init()
        self.add_task("a", mutates=1, scope="src/app")
        path = self.root / "contract.yaml"
        path.write_text(
            "task_id: a\n"
            "role: worker\n"
            "objective: Wire controller navigation into Big Picture\n"
            "write_scope:\n  - src/app/**\n"
            'read_scope: ["**"]\n'
            "forbidden_scope:\n  - backend/**\n"
            "acceptance_criteria:\n"
            "  - controller navigation works\n"
            "  - keyboard navigation still works\n"
            "required_checks:\n  - typecheck\n"
            "when_blocked: report the blocked reason to the orchestrator\n",
            encoding="utf-8")
        r = self.orch("contract", "--id", "a", "--file", str(path))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        contract = json.loads((self.root / ".orchestrator" / "contracts" / "a.json")
                              .read_text(encoding="utf-8"))
        self.assertEqual(contract["write_scope"], ["src/app/**"])
        self.assertEqual(contract["read_scope"], ["**"])
        self.assertEqual(len(contract["acceptance_criteria"]), 2)
        self.assertEqual(contract["forbidden_scope"], ["backend/**"])

    def test_forced_ready_without_a_contract_is_recorded_never_silent(self):
        self.init()
        self.add_task("a", mutates=1)
        r = self.orch("set-task", "--id", "a", "--status", "ready", "--force",
                      "--note", "trivial follow-up, done in DIRECT mode")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("task_direct_override", [e["event"] for e in self.events()])
        decisions = (self.root / ".orchestrator" / "decisions.md").read_text(encoding="utf-8")
        self.assertIn("forced ready without a valid contract", decisions)


class TestScopeEnforcement(OrchTestCase):
    """Layer B (detection) and Layer A (prevention) of scope enforcement."""

    def test_scope_pass_and_machine_readable_json(self):
        self.init()
        wt, branch, commit = self.prepare_task("a", files={"src/app/nav.ts": "export const a=1\n"})
        r = self.orch("validate-scope", "--id", "a", "--json")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        payload = json.loads(r.stdout)
        self.assertEqual(payload["status"], "PASS")
        self.assertIn("src/app/nav.ts", payload["changed"])
        self.assertEqual(payload["unexpected"], [])
        self.assertEqual(payload["forbidden"], [])
        self.assertEqual(payload["task_id"], "a")
        self.assertTrue(payload["base"] and payload["head"])
        self.assertEqual(self.task_json("a")["scope_validation"]["status"], "PASS")

    def test_file_outside_write_scope_is_a_violation(self):
        self.init()
        wt, branch, commit = self.prepare_task("a")
        self.commit_files(wt, {"infra/deploy.yml": "env: prod\n"}, "touched infra")
        r = self.orch("validate-scope", "--id", "a")
        self.assertEqual(r.returncode, 1)
        self.assertIn("SCOPE: FAIL", r.stdout)
        self.assertIn("unexpected:", r.stdout)
        self.assertIn("infra/deploy.yml", r.stdout)
        self.assertIn("SCOPE_VIOLATION", r.stdout)
        violations = [e for e in self.events() if e["event"] == "scope_violation"]
        self.assertEqual(violations[-1]["path"], "infra/deploy.yml")
        self.assertEqual(violations[-1]["kind"], "unexpected")

    def test_forbidden_scope_is_violated_even_inside_write_scope(self):
        self.init()
        self.add_task("a", mutates=1, scope="src")
        wt, branch, commit = self.make_worktree("a", files={"src/legacy/old.ts": "old\n"})
        self.make_contract("a", worktree=str(wt), branch=branch, write_scope=("src/**",),
                           forbidden=("src/legacy/**",))
        r = self.orch("validate-scope", "--id", "a", "--json")
        self.assertEqual(r.returncode, 1)
        payload = json.loads(r.stdout)
        self.assertEqual(payload["forbidden"], ["src/legacy/old.ts"])
        self.assertEqual(payload["allowed"], [])
        self.assertEqual(payload["violations"][0]["kind"], "forbidden")

    def test_glob_semantics_double_star_crosses_directories(self):
        self.init()
        sys.path.insert(0, str(HERE))
        import scope_guard as SG
        self.assertTrue(SG.path_matches("src/app/a/b.ts", "src/app/**"))
        self.assertTrue(SG.path_matches("src/app/main.ts", "src/app/**"))
        self.assertTrue(SG.path_matches("src/ui/button.ts", "src/ui"))
        self.assertFalse(SG.path_matches("src/appx/a.ts", "src/app/**"))
        self.assertFalse(SG.path_matches("src/app/a/b.ts", "src/app/*.ts"))
        self.assertTrue(SG.path_matches("any/deep/path.ts", "**"))

    def test_pre_commit_scope_gate_blocks_out_of_scope_commits(self):
        """Layer A: real mechanical prevention inside the worker's own worktree."""
        self.init()
        wt, branch, commit = self.prepare_task("a")
        r = self.orch("guard", "--id", "a", "--install-hook")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        payload = json.loads(r.stdout)
        self.assertTrue(payload["hook"]["installed"])
        self.assertIn("--worktree", payload["hook"]["mechanism"])
        # the shared checkout's hooks path is untouched (no project-wide side effect)
        r = git(["config", "--get", "core.hooksPath"], self.root)
        self.assertNotEqual(r.returncode, 0, r.stdout)
        # an out-of-scope commit is refused before it reaches history
        Path(wt, "backend").mkdir(exist_ok=True)
        (Path(wt) / "backend" / "auth.ts").write_text("x\n", encoding="utf-8")
        git(["add", "-A"], wt)
        r = git(["commit", "-m", "out of scope"], wt)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("SCOPE_GUARD", r.stderr)
        self.assertIn("backend/auth.ts", r.stderr)
        self.assertEqual(self.gitc("rev-parse", "HEAD", cwd=wt), commit)   # history unspoiled
        # the gate keeps refusing until the offending path is reverted (the correct worker action)
        r = git(["commit", "-m", "still staged"], wt)
        self.assertNotEqual(r.returncode, 0)
        git(["reset", "-q", "HEAD", "--", "backend/auth.ts"], wt)
        (Path(wt) / "backend" / "auth.ts").unlink()
        # an in-scope commit now passes
        self.commit_files(wt, {"src/app/nav.ts": "export const nav = 1\n"}, "in scope")
        self.assertNotEqual(self.gitc("rev-parse", "HEAD", cwd=wt), commit)
        self.assertIn("scope_guard_installed", [e["event"] for e in self.events()])

    def test_no_verify_bypass_is_still_caught_by_detection(self):
        self.init()
        wt, branch, commit = self.prepare_task("a")
        self.orch("guard", "--id", "a", "--install-hook")
        Path(wt, "backend").mkdir(exist_ok=True)
        (Path(wt) / "backend" / "auth.ts").write_text("x\n", encoding="utf-8")
        git(["add", "-A"], wt)
        r = git(["commit", "--no-verify", "-m", "bypass attempt"], wt)
        self.assertEqual(r.returncode, 0)                    # the documented bypass
        r = self.orch("validate-scope", "--id", "a")          # ...and detection catches it
        self.assertEqual(r.returncode, 1)
        self.assertIn("backend/auth.ts", r.stdout)

    def test_prevention_plan_is_generated_from_the_contract(self):
        self.init()
        self.prepare_task("a")
        r = self.orch("guard", "--id", "a", "--plan")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        plan = json.loads(r.stdout)["prevention_plan"]
        # A versão instalada do opencode recusa o env gerado: o plano tem de dizer a verdade em vez
        # de anunciar prevenção mecânica que o worker não consegue nem iniciar.
        self.assertEqual(plan["prevention"], "none")
        self.assertEqual(plan["kind"], "opencode")
        self.assertEqual(plan["launch_env"], {})
        self.assertTrue(any("rejects the generated configuration" in lim
                            for lim in plan["limitations"]), plan["limitations"])
        self.assertTrue(any("commit gate" in lim for lim in plan["limitations"]))
        # As regras continuam implementadas e continuam testáveis fora da CLI.
        import sys as _sys
        _sys.path.insert(0, str(Path(__file__).resolve().parent))
        import scope_guard as sg
        permission = sg.opencode_permission({"task_id": "a", "write_scope": ["src/app/**"],
                                            "forbidden_scope": ["backend/**"]})
        self.assertEqual(permission["edit"]["*"], "deny")
        self.assertEqual(permission["edit"]["src/app/**"], "allow")
        self.assertEqual(permission["edit"]["backend/**"], "deny")
        self.assertEqual(permission["external_directory"]["*"], "deny")

    def test_launch_verification_rejects_unusable_payloads_without_crashing(self):
        self.init()
        self.prepare_task("a")
        r = self.orch("guard", "--id", "a", "--verify-launch", "--observed",
                      '{"edit":{"*":"allow"}}')
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertFalse(json.loads(r.stdout)["launch_verification"]["verified"])
        # Payload sem regra de edit: motivo explícito, nunca AttributeError (era o crash da 537).
        import sys as _sys
        _sys.path.insert(0, str(Path(__file__).resolve().parent))
        import scope_guard as sg
        original = dict(sg.KIND_ADAPTERS["opencode"])
        sg.KIND_ADAPTERS["opencode"] = {k: v for k, v in original.items() if k != "env_status"}
        try:
            out = sg.verify_launch({"task_id": "a", "write_scope": ["src/**"]}, "opencode",
                                   observed='{"foo": 1}')
            self.assertFalse(out["verified"])
            self.assertIn("carries no edit rule map", " ".join(out["reasons"]))
        finally:
            sg.KIND_ADAPTERS["opencode"] = original
        r = self.orch("guard", "--id", "a", "--verify-launch", "--observed", "nao-e-json")
        self.assertEqual(r.returncode, 1)
        self.assertFalse(json.loads(r.stdout)["launch_verification"]["verified"])

    def test_kind_without_a_verified_mechanism_reports_no_prevention(self):
        self.init()
        self.prepare_task("a")
        r = self.orch("guard", "--id", "a", "--plan", "--kind", "some-unknown-cli")
        self.assertEqual(r.returncode, 0)
        plan = json.loads(r.stdout)["prevention_plan"]
        self.assertEqual(plan["prevention"], "none")
        self.assertTrue(any("no verified write-boundary mechanism" in lim
                            for lim in plan["limitations"]))
        adapters = json.loads(self.orch("guard", "--id", "a", "--plan").stdout)
        self.assertEqual(adapters["prevention_plan"]["kind"], "opencode")


class TestMergeGate(OrchTestCase):
    """MERGE GATE: every condition must hold, and the decision is recorded."""

    def test_gate_ready_allows_integration(self):
        self.init()
        wt, branch, commit = self.prepare_task("a")
        self.close_gate("a")
        r = self.orch("merge-gate", "--id", "a", "--live", "--json")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        gate = json.loads(r.stdout)
        for key in ("contract", "result", "scope", "tests", "review", "worktree", "commit",
                    "blockers", "fix_cycles"):
            self.assertIn(key, gate["fields"])
        self.assertTrue(gate["ready"])
        self.assertEqual(gate["reasons"], [])
        r = self.orch("set-task", "--id", "a", "--status", "integrated", "--commit", commit)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        task = self.task_json("a")
        self.assertEqual(task["status"], "integrated")
        self.assertTrue(task["merge_gate"]["ready"])
        self.assertIn("merge_gate_evaluated", [e["event"] for e in self.events()])

    def test_gate_refuses_scope_fail_and_blocks_integration(self):
        self.init()
        wt, branch, commit = self.prepare_task("a")
        self.commit_files(wt, {"infra/deploy.yml": "env: prod\n"}, "out of scope")
        self.close_gate("a")
        r = self.orch("merge-gate", "--id", "a", "--live")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("ready: false", r.stdout, r.stdout + r.stderr)
        self.assertIn("scope=fail", r.stdout)
        self.assertIn("DO NOT MERGE", r.stdout)
        r = self.orch("set-task", "--id", "a", "--status", "integrated", "--commit", commit)
        self.assertEqual(r.returncode, 2)
        self.assertIn("MERGE GATE NOT READY", r.stderr)
        # only an explicit, recorded override can bypass it
        r = self.orch("set-task", "--id", "a", "--status", "integrated", "--commit", commit,
                      "--force", "--note", "user accepted the infra edit")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("merge_gate_bypassed", [e["event"] for e in self.events()])
        decisions = (self.root / ".orchestrator" / "decisions.md").read_text(encoding="utf-8")
        self.assertIn("merge gate BYPASSED", decisions)

    def test_gate_refuses_review_fail(self):
        self.init()
        wt, branch, commit = self.prepare_task("a")
        self.close_gate("a", verdict="FAIL")
        r = self.orch("merge-gate", "--id", "a", "--live")
        self.assertEqual(r.returncode, 1)
        self.assertIn("review=fail", r.stdout)

    def test_gate_refuses_missing_tests_dirty_worktree_and_missing_result(self):
        self.init()
        wt, branch, commit = self.prepare_task("a")
        r = self.orch("merge-gate", "--id", "a", "--live")
        self.assertEqual(r.returncode, 1)
        for reason in ("result=missing", "tests=missing", "review=missing"):
            self.assertIn(reason, r.stdout)
        self.close_gate("a")
        (Path(wt) / "src" / "app" / "dirty.txt").write_text("uncommitted\n", encoding="utf-8")
        r = self.orch("merge-gate", "--id", "a", "--live")
        self.assertEqual(r.returncode, 1)
        self.assertIn("worktree=dirty", r.stdout)

    def test_validation_refuses_an_integration_that_ignored_the_gate(self):
        self.init()
        wt, branch, commit = self.prepare_task("a")
        self.close_gate("a", verdict="FAIL")
        r = self.orch("set-task", "--id", "a", "--status", "integrated", "--commit", commit,
                      "--force", "--note", "user accepted")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        r = self.orch("validate", "--no-herdr")
        self.assertEqual(r.returncode, 1)
        self.assertIn("integrated with a merge gate that is not ready", r.stdout)


class TestCheckpointsAndResume(OrchTestCase):
    """CHECKPOINTS: long tasks survive death, provider failure and context loss."""

    def test_checkpoint_persist_reload_and_history(self):
        self.init()
        wt, branch, commit = self.prepare_task("a")
        r = self.orch("checkpoint", "--id", "a", "--set", "--phase", "3", "--total-phases", "5",
                      "--completed", "schema updated", "--completed", "service layer migrated",
                      "--current", "API integration", "--remaining", "tests",
                      "--remaining", "cleanup", "--decision", "kept the old API for now",
                      "--commit", commit)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        path = self.root / ".orchestrator" / "checkpoints" / "a.json"
        cp = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(cp["phase"], 3)
        self.assertEqual(cp["total_phases"], 5)
        self.assertEqual(cp["completed"], ["schema updated", "service layer migrated"])
        self.assertEqual(cp["remaining"], ["tests", "cleanup"])
        self.assertEqual(cp["current"], ["API integration"])
        self.assertEqual(cp["last_known_commit"], commit)
        self.assertEqual(cp["decisions"], ["kept the old API for now"])
        # survives a fresh process (recovery) and is mirrored in the task state
        r = self.orch("checkpoint", "--id", "a", "--show", "--json")
        self.assertEqual(json.loads(r.stdout)["phase"], 3)
        self.assertEqual(self.task_json("a")["checkpoint"]["phase"], 3)
        self.assertIn("checkpoint_created", [e["event"] for e in self.events()])
        # a later checkpoint archives the previous one instead of losing it
        self.orch("checkpoint", "--id", "a", "--set", "--phase", "4", "--completed",
                  "API integration", "--remaining", "cleanup")
        history = (self.root / ".orchestrator" / "checkpoints" / "a.history.jsonl") \
            .read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(history), 1)
        self.assertEqual(json.loads(history[0])["phase"], 3)
        self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["phase"], 4)
        r = self.orch("checkpoint", "--id", "a", "--list")
        self.assertIn("a.json", r.stdout)

    def test_checkpoint_from_a_yaml_file_with_the_documented_shape(self):
        self.init()
        self.prepare_task("a")
        path = self.root / "cp.yaml"
        path.write_text(
            "checkpoint:\n"
            "  task_id: a\n"
            "  phase: 2\n"
            "  total_phases: 4\n"
            "  completed:\n    - schema updated\n"
            "  current:\n    - API integration\n"
            "  remaining:\n    - tests\n    - cleanup\n"
            "  decisions:\n    - no new dependency added\n"
            "  blockers: []\n", encoding="utf-8")
        r = self.orch("checkpoint", "--id", "a", "--set", "--file", str(path))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        cp = json.loads((self.root / ".orchestrator" / "checkpoints" / "a.json")
                        .read_text(encoding="utf-8"))
        self.assertEqual(cp["phase"], 2)
        self.assertEqual(cp["remaining"], ["tests", "cleanup"])
        self.assertEqual(cp["decisions"], ["no new dependency added"])

    def test_invalid_checkpoint_is_refused(self):
        self.init()
        self.prepare_task("a")
        r = self.orch("checkpoint", "--id", "a", "--set", "--phase", "9", "--total-phases", "2")
        self.assertEqual(r.returncode, 2)
        self.assertIn("CHECKPOINT_INVALID", r.stderr)
        self.assertFalse((self.root / ".orchestrator" / "checkpoints" / "a.json").exists())


class TestWorkerReplacement(OrchTestCase):
    """REPLACEMENT: reconstruct reality, never 'continue where the other one stopped'."""

    def test_replacement_records_history_and_reconstructs_state(self):
        self.init()
        wt, branch, commit = self.prepare_task("a")
        self.orch("checkpoint", "--id", "a", "--set", "--phase", "2", "--total-phases", "4",
                  "--remaining", "tests", "--blocker", "provider unavailable")
        r = self.orch("replace-worker", "--id", "a", "--agent", "w_a2", "--old-agent", "w_a",
                      "--pane", "w9:p3", "--reason", "provider 503", "--no-herdr")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        task = self.task_json("a")
        self.assertEqual(task["replacement_count"], 1)
        self.assertEqual(task["current_worker"]["agent"], "w_a2")
        self.assertEqual(task["agent"], "w_a2")
        self.assertEqual(task["status"], "dispatched")
        self.assertEqual(len(task["worker_history"]), 1)
        self.assertEqual(task["worker_history"][0]["reason"], "provider 503")
        self.assertEqual(task["worker_history"][0]["last_checkpoint_phase"], 2)
        for needle in ("TASK CONTRACT (unchanged):", "write_scope:",
                       "commits on the branch since base:", "LATEST CHECKPOINT", "REMAINING WORK",
                       "One writer per worktree"):
            self.assertIn(needle, r.stdout)
        self.assertIn("report the blocked reason", r.stdout)
        self.assertIn("worker_replaced", [e["event"] for e in self.events()])
        self.assertTrue((self.root / ".orchestrator" / "reports" / "a-replacement-1.txt").is_file())
        self.assertIn("w_a2", self.state()["resources"]["owned_agents"])

    def test_replacement_is_refused_while_the_old_worker_is_still_live(self):
        self.init()
        self.prepare_task("a")
        bin_dir = self.root.parent / "bin"
        bin_dir.mkdir(exist_ok=True)
        fake = bin_dir / "herdr"
        fake.write_text("#!/bin/sh\necho '{\"result\":{\"agents\":[{\"name\":\"w_a\","
                        "\"agent\":\"opencode\",\"agent_status\":\"working\"}]}}'\n", encoding="utf-8")
        fake.chmod(0o755)
        env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}"}
        r = subprocess.run([PY, str(ORCH), "--repo-root", str(self.root), "replace-worker",
                            "--id", "a", "--agent", "w_a2", "--reason", "assumed dead"],
                           capture_output=True, text=True, env=env)
        self.assertEqual(r.returncode, 2)
        self.assertIn("still live", r.stderr)
        r = subprocess.run([PY, str(ORCH), "--repo-root", str(self.root), "replace-worker",
                            "--id", "a", "--agent", "w_a2", "--reason", "old worker stopped by hand",
                            "--force"], capture_output=True, text=True, env=env)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue(self.task_json("a")["worker_history"][0]["live_at_replacement"])

    def test_replacement_requires_a_contract(self):
        self.init()
        self.add_task("a", mutates=1)
        r = self.orch("replace-worker", "--id", "a", "--agent", "w_a2", "--no-herdr")
        self.assertEqual(r.returncode, 2)
        self.assertIn("no contract", r.stderr)


class TestStateMigrationAndRecovery(OrchTestCase):
    """State v1.1 -> v1.2: load, migrate, and never lose contracts or checkpoints."""

    def test_legacy_state_is_migrated_with_defaults_and_nothing_is_dropped(self):
        self.init("--run-id", "t-1")
        wt, branch, commit = self.prepare_task("a")
        self.orch("checkpoint", "--id", "a", "--set", "--phase", "2", "--total-phases", "4",
                  "--remaining", "cleanup")
        digest = self.task_json("a")["contract_digest"]
        state_path = self.root / ".orchestrator" / "state.json"
        legacy = json.loads(state_path.read_text(encoding="utf-8"))
        for key in ("coordination_mode", "team_mode", "worker_execution_mode", "team_constraints",
                    "watchdog", "migration"):
            legacy.pop(key, None)
        legacy["version"] = 1
        state_path.write_text(json.dumps(legacy, indent=2), encoding="utf-8")
        r = self.orch("validate", "--no-herdr")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("legacy state.json", r.stdout)
        self.assertIn("version 1", r.stdout)
        r = self.orch("status", "--json")
        state = json.loads(r.stdout)["state"]
        self.assertEqual(state["coordination_mode"], "supervised_auto")
        self.assertEqual(state["team_mode"], "semi_auto")
        self.assertEqual(state["watchdog"]["stall_after"], 900)
        # a write persists the migration
        self.orch("set-modes", "--team-mode", "semi_auto")
        persisted = json.loads(state_path.read_text(encoding="utf-8"))
        self.assertEqual(persisted["version"], 3)
        self.assertIn("watchdog", persisted)
        # contract + checkpoint survived the migration untouched
        task = self.task_json("a")
        self.assertEqual(task["contract_digest"], digest)
        self.assertEqual(task["checkpoint"]["phase"], 2)
        self.assertEqual(task["contract"]["write_scope"], ["src/app/**"])

    def test_recovery_preserves_contracts_checkpoints_and_worker_history(self):
        self.init("--run-id", "t-1")
        wt, branch, commit = self.prepare_task("a")
        self.orch("checkpoint", "--id", "a", "--set", "--phase", "3", "--total-phases", "5",
                  "--remaining", "tests")
        self.orch("replace-worker", "--id", "a", "--agent", "w_a2", "--old-agent", "w_a",
                  "--reason", "pane disappeared", "--no-herdr")
        digest = self.task_json("a")["contract_digest"]
        # a brand-new session reads the state from disk only
        state = json.loads(self.orch("status", "--json").stdout)
        task = state["tasks"]["tasks"][0]
        self.assertEqual(task["contract_digest"], digest)
        self.assertEqual(task["contract"]["write_scope"], ["src/app/**"])
        self.assertEqual(task["checkpoint"]["phase"], 3)
        self.assertEqual(task["replacement_count"], 1)
        self.assertEqual(task["worker_history"][0]["reason"], "pane disappeared")
        # the reviewer's yardstick is re-rendered identically after the restart
        r = self.orch("contract", "--id", "a", "--show")
        self.assertIn("src/app/**", r.stdout)
        r = self.orch("reconcile", "--no-herdr")
        self.assertIn(r.returncode, (0, 1))          # must not crash on recovered state
        r = self.orch("validate", "--no-herdr")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


class TestEventLogAndReviewPackage(OrchTestCase):
    """The structured event log and the reviewer's contract-driven package."""

    def test_known_events_only_and_full_record_shape(self):
        self.init()
        self.add_task("a")
        r = self.orch("event", "--event", "worker_stalled", "--task", "a",
                      "--data", "reason=no output for 15m")
        self.assertEqual(r.returncode, 0, r.stderr)
        r = self.orch("event", "--event", "not_a_real_event", "--task", "a")
        self.assertEqual(r.returncode, 2)
        self.assertIn("unknown event", r.stderr)
        r = self.orch("event", "--event", "not_a_real_event", "--task", "a", "--allow-unknown")
        self.assertEqual(r.returncode, 0, r.stderr)
        rec = [e for e in self.events() if e["event"] == "worker_stalled"][-1]
        for key in ("time", "run_id", "event", "task", "task_id", "reason"):
            self.assertIn(key, rec)
        self.assertEqual(rec["run_id"], "t-1")
        r = self.orch("events", "--kind", "worker_stalled", "--json")
        self.assertEqual(json.loads(r.stdout)[-1]["event"], "worker_stalled")

    def test_secret_shaped_event_data_is_redacted(self):
        self.init()
        self.add_task("a")
        self.orch("event", "--event", "worker_working", "--task", "a",
                  "--data", "token=abcdef123456", "--data", "details=normal")
        rec = self.events()[-1]
        self.assertNotIn("token", rec)
        self.assertIn("redacted", rec)
        self.assertEqual(rec["details"], "normal")

    def test_review_package_carries_the_contract_and_the_evidence(self):
        self.init()
        wt, branch, commit = self.prepare_task("a", acceptance=("navigation works",))
        self.close_gate("a")
        r = self.orch("review-package", "--id", "a")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        for needle in ("TASK CONTRACT (the yardstick", "write_scope:", "src/app/**",
                       "base commit:", "worker commit:", "scope validation: PASS",
                       "ACCEPTANCE CRITERIA", "navigation works: PASS | FAIL",
                       "verdict: PASS | FAIL", "blocking_findings", "scope_findings",
                       "READ-ONLY reviewer", "Do not edit, format, commit"):
            self.assertIn(needle, r.stdout)
        self.assertIn("review_started", [e["event"] for e in self.events()])
        self.assertTrue((self.root / ".orchestrator" / "reports" / "a-review-package.txt").is_file())

    def test_review_package_requires_a_contract(self):
        self.init()
        self.add_task("a", mutates=1)
        r = self.orch("review-package", "--id", "a")
        self.assertEqual(r.returncode, 2)
        self.assertIn("no contract", r.stderr)


class TestRolePolicies(OrchTestCase):
    """ROLE POLICIES: the default mutation policy per role is explicit and persisted."""

    def test_default_mutation_policy_per_role(self):
        self.init()
        for tid, role, expected in (("w", "worker", "worktree_only"),
                                    ("f", "fixer", "worktree_only"),
                                    ("r", "reviewer", "read_only"),
                                    ("t", "tester", "temp_dirs_only"),
                                    ("q", "researcher", "read_only")):
            self.add_task(tid, role=role, mutates=1 if role in ("worker", "fixer") else 0)
            self.make_contract(tid, role=role, write_scope=("src/app/**",) if role in
                               ("worker", "fixer") else ())
            self.assertEqual(self.task_json(tid)["contract"]["mutation_policy"], expected)
        self.assertIn("reviewer", contracts.ROLE_POLICIES)
        self.assertIn("edit code", contracts.ROLE_POLICIES["reviewer"]["may_not"])
        self.assertIn("expand its own scope", contracts.ROLE_POLICIES["worker"]["may_not"])
        self.assertIn("temp/build/cache", contracts.ROLE_POLICIES["tester"]["write_zone"])


class TestScopeOverlap(OrchTestCase):
    """Invariant (v1.4): two live writers whose write scopes can match the same path are
    refused before dispatch — collisions are caught at planning time, not at merge time."""

    def test_prefix_collision_is_refused_with_exit_2(self):
        self.init()
        self.add_task("a", scope="src/app/**")
        self.add_task("b", scope="src/app/foo.ts")     # a strict prefix of the other
        r = self.orch("overlap")
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("OVERLAP: 1 COLLISION", r.stdout)
        r = self.orch("overlap", "--json")
        data = json.loads(r.stdout)
        self.assertEqual(data["collisions"][0]["confidence"], "definite")
        self.assertEqual(sorted(data["collisions"][0]["tasks"]), ["a", "b"])

    def test_disjoint_scopes_are_clean(self):
        self.init()
        self.add_task("a", scope="src/app/**")
        self.add_task("b", scope="src/db/**")
        r = self.orch("overlap")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("OVERLAP: NONE", r.stdout)

    def test_finished_tasks_do_not_count(self):
        self.init()
        self.add_task("a", scope="src/app/**")
        self.add_task("b", scope="src/app/foo.ts")
        self.orch("set-task", "--id", "a", "--status", "cancelled")
        r = self.orch("overlap")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("OVERLAP: NONE", r.stdout)


class TestNumericIdentifiers(OrchTestCase):
    """Invariant (v1.4): a short commit sha that happens to be all digits is TEXT, never a number.
    The tolerant YAML subset coerced `commit: 3775697` to int, and the merge gate then crashed with
    `TypeError: expected str, bytes or os.PathLike object, not int` (~4% of 7-char shas)."""

    def test_result_report_with_a_numeric_sha_stays_text(self):
        res = contracts.parse_result("result: DONE\ntask_id: a\ncommit: 3775697\n"
                                     "changed_files: []\ntests: []\nscope_violations: []\n"
                                     "blockers: []\nnotes: []\n")
        self.assertEqual(res["commit"], "3775697")
        self.assertIsInstance(res["commit"], str)

    def test_numeric_commit_sha_does_not_crash_the_gate(self):
        self.init()
        wt, branch, commit = self.prepare_task("a")
        self.close_gate("a", verdict="FAIL")
        path = self.root / ".orchestrator" / "tasks.json"      # the coerced form the parser produced
        data = json.loads(path.read_text(encoding="utf-8"))
        data["tasks"][0]["commit"] = 3775697
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        r = self.orch("merge-gate", "--id", "a", "--live")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("review=fail", r.stdout)                 # a normal verdict...
        self.assertEqual(r.stderr.strip(), "")                 # ...not a traceback


if __name__ == "__main__":
    unittest.main(verbosity=2)
