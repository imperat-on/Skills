#!/usr/bin/env python3
"""Orchestrator state manager (stdlib only, no network, no secrets).

Keeps .orchestrator/{state.json,tasks.json,events.jsonl,decisions.md,reports/,contracts/,
checkpoints/,guards/,watchdog/,skill-proposals.md} honest so a lost Hermes session can be
reconstructed from Git + Herdr reality. Every write is atomic; the event log is append-only and
shared with the watchdog.

Commands:
  init             create .orchestrator/, detect git facts, exclude the dir from git, record config
  set-modes        change coordination_mode / team_mode / worker_execution_mode / team_constraints
  modes            print the current run configuration
  propose          record a candidate lesson about the orchestrator skill (never edits the skill)
  add-task         add a task to the graph
  set-task         update a task (status, agent, pane, workspace, worktree, branch, commit, ...)
  contract         write/validate/show the structured task contract for a task
  result           collect and validate a worker's structured result report
  verify           independent, mechanical verification of a task (git + scope) -> recorded evidence
  validate-scope   compare the contract with the real diff (SCOPE: PASS/FAIL, machine-readable)
  merge-gate       compute the integration gate (ready: true/false) and persist it
  guard            install/plan/verify the run-owned scope guards for a task's worker
  checkpoint       persist/show/list a worker checkpoint (long tasks, resume, replacement)
  replace-worker   record a worker replacement and print the reconstructed recovery package
  review-package   serialize the contract + evidence the independent reviewer must judge
  events           tail/filter the structured event log
  event            append an event to events.jsonl
  ready            list tasks whose dependencies are satisfied and whose contract is valid
  status           print the task table
  reconcile        compare persisted state with Git + Herdr reality (read-only, prints discrepancies)
  report           render the final run report skeleton from persisted state
  validate         schema/consistency check of the local state files

Exit codes: 0 ok, 1 discrepancies/invalid state/gate not ready, 2 usage/setup error.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import contracts as C  # noqa: E402
import events as events_mod  # noqa: E402
import scope_guard as SG  # noqa: E402

STATUSES = [
    "pending", "ready", "dispatched", "working", "blocked", "review",
    "failed", "needs_fix", "passed", "integrated", "cancelled",
]
ROLES = ["worker", "researcher", "tester", "reviewer", "fixer"]
DEP_SATISFIED = {"passed", "integrated"}
ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")

# --- run configuration: three orthogonal axes (see references/coordination-modes.md,
# references/team-composition.md, references/worker-execution-modes.md)
STATE_VERSION = 3           # 2 -> 3: contracts, checkpoints, scope validation, merge gate, worker history
COORDINATION_MODES = ["assisted", "supervised_auto", "auto"]
TEAM_MODES = ["manual", "semi_auto", "auto"]
WORKER_EXECUTION_MODES = ["autonomous", "interactive"]
DEFAULT_COORDINATION_MODE = "supervised_auto"
DEFAULT_TEAM_MODE = "semi_auto"
DEFAULT_WORKER_EXECUTION_MODE = "autonomous"

PROPOSAL_KINDS = ["pitfall", "improvement", "flag-discovery", "default-change", "doc-fix"]
MODE_KEYS = ("coordination_mode", "team_mode", "worker_execution_mode", "team_constraints")

TASK_NEW_FIELDS = {
    "contract": None,
    "contract_digest": None,
    "result": None,
    "checkpoint": None,
    "scope_validation": None,
    "merge_gate": None,
    "verification": None,
    "tests": None,
    "worktree_clean": None,
    "changed_files": [],
    "blockers": [],
    "fix_cycles_open": 0,
    "worker_history": [],
    "current_worker": None,
    "replacement_count": 0,
    "last_activity": None,
}

DEFAULT_WATCHDOG = {"stall_after": 900, "dead_grace": 60, "idle_grace": 60}
SUB_DIRS = ["reports", "contracts", "checkpoints", "guards", "watchdog"]


def now() -> str:
    return C.now()


def fail(msg: str, code: int = 2):
    print(msg, file=sys.stderr)
    sys.exit(code)


def run(cmd, cwd=None) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=60)
        return p.returncode, (p.stdout or p.stderr).strip()
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 127, str(exc)


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp-", suffix="-" + path.name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def orch_dir(root: Path) -> Path:
    return root / ".orchestrator"


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def require_state(root: Path):
    d = orch_dir(root)
    if not (d / "state.json").exists():
        fail(f"no orchestrator state at {d/'state.json'} — run `init` first")
    return d


def default_constraints() -> dict:
    return {"allowed_agent_kinds": [], "pinned_roles": {}, "max_workers": None, "notes": []}


def normalize_task(task: dict) -> list:
    """Fill in the v3 task fields (legacy state) and report what was assumed."""
    assumed = []
    for field, default in TASK_NEW_FIELDS.items():
        if field not in task:
            task[field] = json.loads(json.dumps(default)) if isinstance(default, (list, dict)) \
                else default
            assumed.append(field)
    if task.get("contract"):
        task["contract"] = C.normalize_contract(task["contract"], task.get("id"))
        if not task.get("contract_digest"):
            task["contract_digest"] = C.contract_digest(task["contract"])
    if task.get("current_worker") is None and task.get("agent"):
        task["current_worker"] = {"agent": task.get("agent"), "pane": task.get("pane"),
                                  "workspace": task.get("workspace"), "since": task.get("updated_at")}
    return assumed


def normalize_state(state: dict) -> list:
    """Fill in missing run-configuration keys (legacy state) and report what was assumed.

    Read-only in-memory migration: any later `save` persists the normalized values.
    """
    assumed = []
    if "coordination_mode" not in state:
        state["coordination_mode"] = DEFAULT_COORDINATION_MODE
        assumed.append("coordination_mode")
    if "team_mode" not in state:
        state["team_mode"] = DEFAULT_TEAM_MODE
        assumed.append("team_mode")
    if "worker_execution_mode" not in state:
        state["worker_execution_mode"] = DEFAULT_WORKER_EXECUTION_MODE
        assumed.append("worker_execution_mode")
    if "team_constraints" not in state:
        state["team_constraints"] = default_constraints()
        assumed.append("team_constraints")
    else:
        for k, v in default_constraints().items():
            state["team_constraints"].setdefault(k, v)
    if "watchdog" not in state:
        state["watchdog"] = dict(DEFAULT_WATCHDOG)
        assumed.append("watchdog")
    else:
        for k, v in DEFAULT_WATCHDOG.items():
            state["watchdog"].setdefault(k, v)
    if "migration" not in state:
        state["migration"] = {"from_version": state.get("version"),
                              "migrated_at": now(),
                              "note": "state normalised in memory; values are persisted on the next write"}
        assumed.append("migration")
    state.setdefault("version", STATE_VERSION)
    return assumed


def load(root: Path):
    d = require_state(root)
    state = read_json(d / "state.json")
    normalize_state(state)          # in-memory migration; persisted on the next save()
    tasks = read_json(d / "tasks.json")
    for task in tasks.get("tasks", []):
        normalize_task(task)
    return d, state, tasks


def save(root: Path, state, tasks) -> None:
    d = orch_dir(root)
    state["updated_at"] = now()
    state["version"] = STATE_VERSION
    state["tasks"] = [t["id"] for t in tasks["tasks"]]
    for task in tasks["tasks"]:
        normalize_task(task)
    atomic_write(d / "state.json", json.dumps(state, indent=2, sort_keys=False) + "\n")
    atomic_write(d / "tasks.json", json.dumps(tasks, indent=2, sort_keys=False) + "\n")


def log_event(root: Path, event: str, task=None, **data) -> None:
    """Append to the shared event log (flock, redaction, run_id) implemented by events.py."""
    events_mod.log_event(root, event, task=task, **data)


def decide(root: Path, text: str) -> None:
    """Append a timestamped decision line to decisions.md."""
    d = orch_dir(root)
    d.mkdir(parents=True, exist_ok=True)
    path = d / "decisions.md"
    if not path.exists():
        path.write_text(f"# Decisions — run {root.name}\n\n", encoding="utf-8")
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(f"{now()} — {text}\n")


def git_dir(root: Path):
    code, out = run(["git", "rev-parse", "--git-dir"], cwd=root)
    if code != 0:
        return None
    return Path(out) if os.path.isabs(out) else (root / out)


def exclude_orchestrator_dir(root: Path, decision_log: Path) -> str | None:
    """Add .orchestrator/ to .git/info/exclude (never .gitignore). Returns a note or None."""
    gd = git_dir(root)
    if gd is None:
        return None
    info = gd / "info"
    info.mkdir(parents=True, exist_ok=True)
    excl = info / "exclude"
    line = ".orchestrator/"
    current = excl.read_text(encoding="utf-8") if excl.exists() else ""
    if line in {ln.strip() for ln in current.splitlines()}:
        return None
    with open(excl, "a", encoding="utf-8") as fh:
        if current and not current.endswith("\n"):
            fh.write("\n")
        fh.write(f"{line}\n")
    note = f"{now()} — added `{line}` to {excl} (project ignore rules left untouched)."
    with open(decision_log, "a", encoding="utf-8") as fh:
        fh.write(note + "\n")
    return note


def parse_pin(value: str) -> tuple[str, str]:
    if "=" not in value:
        fail(f"invalid --pin {value!r}: expected ROLE=KIND or TASK_ID=KIND")
    key, kind = (p.strip() for p in value.split("=", 1))
    if not key or not kind:
        fail(f"invalid --pin {value!r}: expected ROLE=KIND or TASK_ID=KIND")
    return key, kind


def find_task(tasks, task_id: str):
    return next((t for t in tasks["tasks"] if t["id"] == task_id), None)


def task_contract(task: dict) -> dict:
    contract = task.get("contract")
    if not contract:
        return {}
    return C.normalize_contract(contract, task.get("id"))


def contract_verdict(task: dict) -> dict:
    contract = task_contract(task)
    if not contract:
        return {"task_id": task.get("id"), "mutating": bool(task.get("mutates_files")),
                "valid": False, "errors": ["no contract recorded for this task"],
                "warnings": []}
    verdict = C.validate_contract(contract)
    if task.get("contract_digest") and task["contract_digest"] != C.contract_digest(contract):
        verdict["errors"].append("contract digest mismatch: the recorded material fields were "
                                 "changed after the contract was written (worker-side edit?)")
        verdict["valid"] = False
    return verdict


# --------------------------------------------------------------------------- commands

def cmd_init(a) -> int:
    root = Path(a.repo_root).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    d = orch_dir(root)
    state_path = d / "state.json"
    if state_path.exists() and not a.force:
        fail(f"{state_path} already exists — use `reconcile` to resume, or `init --force` to archive it")
    if state_path.exists() and a.force:
        backup = state_path.with_suffix(f".json.bak-{datetime.now().strftime('%Y%m%d-%H%M%S')}")
        state_path.replace(backup)
        print(f"archived previous state to {backup}")

    code, toplevel = run(["git", "rev-parse", "--show-toplevel"], cwd=root)
    is_git = code == 0
    if is_git:
        _, branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=root)
        _, commit = run(["git", "rev-parse", "HEAD"], cwd=root)
        _, dirty = run(["git", "status", "--porcelain"], cwd=root)
    else:
        toplevel, branch, commit, dirty = None, None, None, ""

    run_id = a.run_id or (datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + (a.slug or "run"))
    constraints = default_constraints()
    if a.allowed_agent_kind:
        constraints["allowed_agent_kinds"] = sorted(set(a.allowed_agent_kind))
    for pin in (a.pin or []):
        key, kind = parse_pin(pin)
        constraints["pinned_roles"][key] = kind
    if a.max_workers is not None:
        constraints["max_workers"] = a.max_workers or None
    if a.constraint_note:
        constraints["notes"].append({"time": now(), "note": a.constraint_note})

    state = {
        "version": STATE_VERSION,
        "run_id": run_id,
        "created_at": now(),
        "updated_at": now(),
        "status": "running",
        "coordination_mode": a.coordination_mode,
        "team_mode": a.team_mode,
        "worker_execution_mode": a.worker_execution_mode,
        "team_constraints": constraints,
        "worktree_root": str(d / "worktrees" / run_id),
        "watchdog": {"stall_after": a.stall_after, "dead_grace": DEFAULT_WATCHDOG["dead_grace"],
                     "idle_grace": DEFAULT_WATCHDOG["idle_grace"],
                     "spin_after": DEFAULT_WATCHDOG.get("spin_after", 1800)},
        "repo": {
            "root": str(root),
            "base_branch": a.base_branch or branch,
            "base_commit": a.base_commit or commit,
            "integration_checkout": a.integration_checkout or str(root),
            "is_git_repo": is_git,
            "dirty_at_start": bool(dirty),
        },
        "orchestrator": {
            "agent_name": a.orchestrator_name,
            "workspace": a.workspace,
            "pane": a.pane,
        },
        "resources": {
            "owned_agents": [], "owned_workspaces": [], "owned_panes": [],
            "owned_worktrees": [], "owned_branches": [],
        },
        "tasks": [],
        "integration": {"completed": [], "pending": []},
    }
    save(root, state, {"tasks": []})
    for sub in SUB_DIRS:
        (d / sub).mkdir(parents=True, exist_ok=True)
    (d / "events.jsonl").touch()
    dec = d / "decisions.md"
    if not dec.exists():
        atomic_write(
            dec,
            f"# Decisions — run {run_id}\n\n"
            f"Repo root: {root}\nBase branch: {state['repo']['base_branch']}\n"
            f"Base commit: {state['repo']['base_commit']}\n\n"
            f"Run configuration: coordination={a.coordination_mode} team={a.team_mode} "
            f"workers={a.worker_execution_mode}\n\n"
            f"Record every deviation from the default policy, every trust grant, every mode change,\n"
            f"every workaround and every escalation here, with a timestamp.\n\n",
        )
    note = exclude_orchestrator_dir(root, dec)
    log_event(root, "run_initialised", run_id=run_id, base_branch=state["repo"]["base_branch"],
              base_commit=state["repo"]["base_commit"],
              coordination_mode=a.coordination_mode, team_mode=a.team_mode,
              worker_execution_mode=a.worker_execution_mode)
    if state["repo"]["dirty_at_start"]:
        log_event(root, "dirty_checkout_at_start")
    print(json.dumps({"run_id": run_id, "root": str(root), "base_branch": state["repo"]["base_branch"],
                      "base_commit": state["repo"]["base_commit"], "git": is_git,
                      "dirty": state["repo"]["dirty_at_start"],
                      "coordination_mode": a.coordination_mode, "team_mode": a.team_mode,
                      "worker_execution_mode": a.worker_execution_mode,
                      "watchdog": state["watchdog"],
                      "team_constraints": constraints, "exclude_note": note}, indent=2))
    return 0


def cmd_set_modes(a) -> int:
    root = Path(a.repo_root).expanduser().resolve()
    d, state, tasks = load(root)
    before = {k: state[k] for k in ("coordination_mode", "team_mode", "worker_execution_mode")}
    before["team_constraints"] = json.loads(json.dumps(state["team_constraints"]))
    changed = []

    for key in ("coordination_mode", "team_mode", "worker_execution_mode"):
        val = getattr(a, key, None)
        if val is not None:
            state[key] = val
            changed.append(key)

    tc = state["team_constraints"]
    if a.allowed_agent_kind:
        tc["allowed_agent_kinds"] = sorted(set(a.allowed_agent_kind))
        changed.append("allowed_agent_kinds")
    if a.clear_allowed_kinds:
        tc["allowed_agent_kinds"] = []
        changed.append("allowed_agent_kinds")
    for pin in (a.pin or []):
        key, kind = parse_pin(pin)
        tc["pinned_roles"][key] = kind
        changed.append(f"pin:{key}")
    for key in (a.unpin or []):
        if key in tc["pinned_roles"]:
            del tc["pinned_roles"][key]
            changed.append(f"unpin:{key}")
    if a.max_workers is not None:
        tc["max_workers"] = a.max_workers or None
        changed.append("max_workers")
    if a.clear_constraints:
        state["team_constraints"] = default_constraints()
        changed.append("team_constraints_reset")
    if a.stall_after is not None:
        state.setdefault("watchdog", dict(DEFAULT_WATCHDOG))["stall_after"] = a.stall_after
        changed.append("watchdog.stall_after")
    note = a.note or "mode/constraint change"
    state["team_constraints"].setdefault("notes", []).append({"time": now(), "note": note})

    if not changed:
        fail("nothing to change: pass at least one of --coordination-mode/--team-mode/"
             "--worker-execution-mode/--allowed-agent-kind/--pin/--unpin/--max-workers/--stall-after")

    save(root, state, tasks)
    log_event(root, "mode_changed", changed=changed,
              coordination_mode=state["coordination_mode"], team_mode=state["team_mode"],
              worker_execution_mode=state["worker_execution_mode"], note=note)
    decide(root, f"run configuration changed ({', '.join(changed)}): "
                 f"coordination={state['coordination_mode']} team={state['team_mode']} "
                 f"workers={state['worker_execution_mode']} — {note}")
    print(json.dumps({k: state[k] for k in MODE_KEYS}, indent=2))
    return 0


def cmd_modes(a) -> int:
    root = Path(a.repo_root).expanduser().resolve()
    d, state, tasks = load(root)
    if a.json:
        print(json.dumps({k: state[k] for k in MODE_KEYS}, indent=2))
        return 0
    print(f"run {state['run_id']}  status={state['status']}")
    print(f"coordination_mode:     {state['coordination_mode']}")
    print(f"team_mode:            {state['team_mode']}")
    print(f"worker_execution_mode: {state['worker_execution_mode']}")
    tc = state["team_constraints"]
    print(f"allowed_agent_kinds:  {tc['allowed_agent_kinds'] or 'any installed kind'}")
    print(f"pinned_roles:         {tc['pinned_roles'] or 'none'}")
    print(f"max_workers:          {tc['max_workers'] if tc['max_workers'] is not None else 'unbounded'}")
    print(f"watchdog.stall_after: {state.get('watchdog', {}).get('stall_after')}s")
    return 0


def cmd_propose(a) -> int:
    """Record a candidate lesson about the orchestrator skill. Never edits the skill."""
    root = Path(a.repo_root).expanduser().resolve()
    d, state, tasks = load(root)
    if a.kind not in PROPOSAL_KINDS:
        fail(f"invalid --kind {a.kind!r}: {', '.join(PROPOSAL_KINDS)}")
    path = d / "skill-proposals.md"
    if not path.exists():
        atomic_write(
            path,
            "# Skill proposals\n\nCandidates recorded during this run. NOT applied automatically: "
            "the herdr-orchestrator skill is edited only when the user asks for it "
            "(see references/self-modification.md).\n",
        )
    status = a.proposal_status or "proposed"
    block = (
        f"\n## [{status}] {a.title}\n"
        f"kind: {a.kind}\n"
        f"task: {a.task or '-'}\n"
        f"time: {now()}\n"
        f"detail: {a.detail or '-'}\n"
    )
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(block)
    log_event(root, "skill_proposal_recorded", task=a.task, kind=a.kind, title=a.title,
              status=status)
    print(f"recorded proposal in {path}")
    print(block.strip())
    return 0


def cmd_add_task(a) -> int:
    root = Path(a.repo_root).expanduser().resolve()
    d, state, tasks = load(root)
    if not ID_RE.match(a.id):
        fail(f"invalid task id {a.id!r}: use lowercase [a-z0-9._-], starting alphanumeric, max 64 chars")
    if any(t["id"] == a.id for t in tasks["tasks"]):
        fail(f"task {a.id!r} already exists")
    if a.role not in ROLES:
        fail(f"invalid role {a.role!r}: {', '.join(ROLES)}")
    known = {t["id"] for t in tasks["tasks"]}
    unknown = [x for x in (a.depends_on or []) if x not in known]
    if unknown:
        fail(f"dependencies not in graph yet: {', '.join(unknown)}")
    task = {
        "id": a.id,
        "title": a.title,
        "role": a.role,
        "status": "pending",
        "agent": None, "workspace": None, "pane": None,
        "worktree": None, "branch": None, "base_commit": None, "commit": None,
        "depends_on": a.depends_on or [],
        "mutates_files": bool(a.mutates),
        "expected_scope": a.scope or [],
        "acceptance": a.acceptance or [],
        "preferred_agent_kind": a.preferred_agent or "auto",
        "worktree_required": a.worktree_required if a.worktree_required is not None else ("auto" if a.mutates else False),
        "worker_execution": None,
        "verified": None, "verdict": None, "report": None, "notes": [],
        "created_at": now(), "updated_at": now(),
    }
    task.update({k: (json.loads(json.dumps(v)) if isinstance(v, (list, dict)) else v)
                 for k, v in TASK_NEW_FIELDS.items()})
    tasks["tasks"].append(task)
    save(root, state, tasks)
    log_event(root, "task_created", task=task["id"], role=task["role"], mutates=task["mutates_files"],
              depends_on=task["depends_on"])
    print(json.dumps(task, indent=2))
    return 0


CONTRACT_FLAG_FIELDS = {
    "objective": "objective", "read_scope": "read_scope", "forbidden_scope": "forbidden_scope",
    "required_check": "required_checks", "deliverable": "deliverables", "when_blocked": "when_blocked",
    "mutation_policy": "mutation_policy", "checkpoint_policy": "checkpoint_policy",
    "phase_plan": "phase_plan", "agent_kind": "agent_kind", "scope_justification": "scope_justification",
    "note": "notes", "model": "model", "budget_tokens": "budget_tokens", "budget_usd": "budget_usd",
}


def _git(root: Path, *args) -> tuple:
    proc = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def cmd_resume(a) -> int:
    """Rebuild a run whose worktree/process disappeared: git reality first, then recreate on demand.

    The filesystem and Git are authoritative; a worker that vanished is reconstructed with facts
    (branch, commits, changed files, checkpoint, remaining acceptance) instead of "continue where
    the other one stopped". Without --recreate this is a read-only diagnosis.
    """
    root = Path(a.repo_root).expanduser().resolve()
    d, state, tasks = load(root)
    task = find_task(tasks, a.id)
    if task is None:
        fail(f"unknown task {a.id!r}")
    branch = task.get("branch")
    base = task.get("base_commit") or (state.get("repo") or {}).get("base_commit")
    run_id = state.get("run_id") or "run"
    wt_root = Path(state.get("worktree_root") or (root / ".orchestrator" / "worktrees" / str(run_id)))
    canon = wt_root / str(a.id)
    recorded = task.get("worktree")
    path = Path(a.path).expanduser().resolve() if a.path else (Path(recorded).expanduser()
                                                               if recorded else canon)
    exists = path.is_dir()
    branch_ok = False
    if branch:
        rc, _out = _git(root, "rev-parse", "--verify", f"refs/heads/{branch}")
        branch_ok = rc == 0
    recreated = False
    if not exists and a.recreate:
        if not branch or not branch_ok:
            fail(f"cannot recreate: branch {branch!r} does not exist in this repository")
        path = path if a.path else canon
        path.parent.mkdir(parents=True, exist_ok=True)
        rc, out = _git(root, "worktree", "add", str(path), branch)
        if rc != 0:
            fail(f"git worktree add failed: {out.strip()}")
        recreated = True
        task["worktree"] = str(path)
        task["updated_at"] = now()
        save(root, state, tasks)
        log_event(root, "worktree_recreated", task=a.id, branch=branch, path=str(path))

    commits, changed = [], []
    if branch and base:
        rc, out = _git(root, "log", "--oneline", f"{base}..{branch}")
        if rc == 0:
            commits = [ln for ln in out.splitlines() if ln.strip()]
        rc, out = _git(root, "diff", "--name-only", f"{base}...{branch}")
        if rc == 0:
            changed = [ln for ln in out.splitlines() if ln.strip()]
    contract = task.get("contract") or {}
    payload = {
        "task_id": a.id,
        "status": task.get("status"),
        "agent": task.get("agent"),
        "branch": branch,
        "base_commit": base,
        "worktree": str(path),
        "worktree_exists": exists,
        "branch_exists": branch_ok,
        "recreated": recreated,
        "commits": commits,
        "changed_files": changed,
        "checkpoint": task.get("checkpoint"),
        "acceptance": contract.get("acceptance_criteria") or task.get("acceptance") or [],
        "write_scope": contract.get("write_scope") or [],
        "advisory": ("reconstructed from Git reality: hand this package to the next worker; never "
                     "reuse a vanished worker's uncommitted work as if it existed"),
    }
    if a.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"RESUME  task={a.id}  branch={branch or '-'}  worktree={path}")
        print(f"  worktree exists={exists}  branch exists={branch_ok}  recreated={recreated}")
        print(f"  commits since base: {len(commits)}")
        for ln in commits[-5:]:
            print(f"    {ln}")
        print(f"  changed files: {len(changed)}")
        for p in changed[:15]:
            print(f"    {p}")
        if payload["checkpoint"]:
            print(f"  checkpoint: {payload['checkpoint']}")
        print("  remaining acceptance criteria:")
        for crit in payload["acceptance"]:
            print(f"    - {crit}")
        if not exists and not a.recreate:
            print("  next: re-run with --recreate to rebuild the worktree from the branch")
    return 0


def cmd_contract(a) -> int:
    """Write (or show) the structured task contract. The contract is the delegation unit."""
    root = Path(a.repo_root).expanduser().resolve()
    d, state, tasks = load(root)
    task = find_task(tasks, a.id)
    if task is None:
        if not a.file:
            fail(f"unknown task {a.id!r}: pass --file (or add the task first)")
        task = None

    if a.show:
        contract = task_contract(task) if task else (SG.load_contract_file(a.file) if a.file else {})
        if not contract:
            fail(f"task {a.id!r} has no contract")
        payload = {"contract": contract, "verdict": C.validate_contract(contract),
                   "rendered": C.render_contract(contract),
                   "digest": C.contract_digest(contract)}
        print(json.dumps(payload, indent=2) if a.json else payload["rendered"])
        return 0 if payload["verdict"]["valid"] else 1

    if a.file:
        try:
            raw = C.load_structured_text(Path(a.file).expanduser().read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            fail(f"cannot read contract file: {exc}")
        raw.setdefault("task_id", a.id)
        dropped = sorted(set((task or {}).get("contract") or {}) - set(raw))
        if dropped:
            print(f"contract file replaces the stored contract: dropping {', '.join(dropped)}",
                  file=sys.stderr)
    else:
        # MERGE, not replacement: an existing contract is the base and only the fields actually
        # passed on this command line win. A partial `--force` (for example only --depends-on) used
        # to erase objective/acceptance/checks, which cost a reviewer its own contract once.
        base = (task or {}).get("contract") or {}
        raw = json.loads(json.dumps(base)) if base else {}
        raw["task_id"] = a.id
        if a.role:
            raw["role"] = a.role
        for flag, field in (("write_scope", "write_scope"), ("acceptance", "acceptance_criteria"),
                            ("depends_on", "depends_on")):
            values = getattr(a, flag, None)
            if values:
                raw[field] = values
        for flag, field in CONTRACT_FLAG_FIELDS.items():
            values = getattr(a, flag, None)
            if not values:
                continue
            raw[field] = values if isinstance(values, list) else values
    raw["task_id"] = a.id
    if task:
        raw.setdefault("branch", task.get("branch"))
        raw.setdefault("worktree", task.get("worktree"))
        raw.setdefault("base_commit", task.get("base_commit") or state["repo"]["base_commit"])
        raw.setdefault("role", task.get("role"))
        if a.worker:
            raw["worker"] = a.worker
    if a.base_commit:
        raw["base_commit"] = a.base_commit
    if a.branch:
        raw["branch"] = a.branch
    if a.worktree:
        raw["worktree"] = a.worktree
    contract = C.normalize_contract(raw, a.id)
    verdict = C.validate_contract(contract)
    digest = C.contract_digest(contract)

    if task is None:
        task = {
            "id": a.id, "title": (contract.get("objective") or a.id)[:80], "role": contract.get("role") or "worker",
            "status": "pending", "agent": None, "workspace": None, "pane": None, "worktree": None,
            "branch": None, "base_commit": None, "commit": None, "depends_on": [],
            "mutates_files": C.is_mutating(contract),
            "expected_scope": contract.get("write_scope") or [],
            "acceptance": contract.get("acceptance_criteria") or [],
            "preferred_agent_kind": contract.get("agent_kind") or "auto",
            "worktree_required": "auto" if C.is_mutating(contract) else False,
            "worker_execution": None, "verified": None, "verdict": None, "report": None,
            "notes": [], "created_at": now(), "updated_at": now(),
        }
        task.update({k: (json.loads(json.dumps(v)) if isinstance(v, (list, dict)) else v)
                     for k, v in TASK_NEW_FIELDS.items()})
        tasks["tasks"].append(task)
        log_event(root, "task_created", task=a.id, role=task["role"],
                  mutates=task["mutates_files"], created_from="contract")
    else:
        previous = task.get("contract")
        if previous and C.contract_digest(previous) != digest and not a.force:
            fail(f"task {a.id!r} already has a material contract ({task.get('contract_digest')}); a "
                 f"material change must go through the orchestrator explicitly — re-run with --force "
                 f"and record why")

    task["contract"] = contract
    task["contract_digest"] = digest
    task["mutates_files"] = C.is_mutating(contract)
    task["expected_scope"] = contract.get("write_scope") or task["expected_scope"]
    task["acceptance"] = contract.get("acceptance_criteria") or task["acceptance"]
    task["role"] = contract.get("role") or task.get("role")
    if contract.get("base_commit") and not task.get("base_commit"):
        task["base_commit"] = contract["base_commit"]
    if contract.get("branch"):
        task["branch"] = contract["branch"]
    if contract.get("worktree"):
        task["worktree"] = contract["worktree"]
    task["updated_at"] = now()

    contract_path = d / "contracts" / f"{a.id}.json"
    atomic_write(contract_path, json.dumps(contract, indent=2) + "\n")
    save(root, state, tasks)
    # ownership ledger for anything the contract itself introduces
    for kind, val in (("owned_worktrees", contract.get("worktree")),
                      ("owned_branches", contract.get("branch"))):
        if val and val not in state["resources"][kind]:
            state["resources"][kind].append(val)
    save(root, state, tasks)

    if verdict["valid"]:
        log_event(root, "contract_written", task=a.id, digest=digest,
                  mutating=verdict["mutating"], policy=contract.get("mutation_policy"),
                  warnings=len(verdict["warnings"]))
    else:
        log_event(root, "contract_invalid", task=a.id, errors=verdict["errors"][:6])
    out = {"task_id": a.id, "contract_file": str(contract_path), "digest": digest,
           "valid": verdict["valid"], "mutating": verdict["mutating"],
           "errors": verdict["errors"], "warnings": verdict["warnings"],
           "checkpoint_required": C.checkpoint_required(contract),
           "rendered": C.render_contract(contract)}
    if a.json:
        print(json.dumps(out, indent=2))
    else:
        print(C.render_contract(contract))
        print()
        print("TASK_CONTRACT: VALID" if verdict["valid"] else "TASK_CONTRACT_INVALID")
        for e in verdict["errors"]:
            print(f"  error: {e}")
        for w in verdict["warnings"]:
            print(f"  warning: {w}")
        if verdict["valid"]:
            print(f"  digest: {digest}  checkpoints: "
                  f"{'required' if C.checkpoint_required(contract) else 'not needed'}")
            print("  NOT delegating? the contract is not a delegation by itself; dispatch is a "
                  "separate, recorded step.")
    return 0 if verdict["valid"] else 1


def cmd_result(a) -> int:
    """Collect the worker's structured result report (communication, never evidence)."""
    root = Path(a.repo_root).expanduser().resolve()
    d, state, tasks = load(root)
    task = find_task(tasks, a.id)
    if task is None:
        fail(f"unknown task {a.id!r}")
    if a.file and a.file != "-":
        try:
            text = Path(a.file).expanduser().read_text(encoding="utf-8")
        except OSError as exc:
            fail(f"cannot read result file: {exc}")
    elif a.file == "-":
        text = sys.stdin.read()
    else:
        text = a.text or ""
    result = C.parse_result(text)
    verdict = C.validate_result(result)
    if result.get("parse_error"):
        verdict["errors"].insert(0, result["parse_error"])
        verdict["valid"] = False
    task["result"] = {**result, "collected_at": now(), "source": a.file or "inline"}
    if result.get("commit"):
        task["commit"] = result["commit"]
    if result.get("blockers"):
        task["blockers"] = sorted(set(list(task.get("blockers") or []) + list(result["blockers"])))
    task["status"] = {"DONE": "review", "BLOCKED": "blocked", "FAILED": "failed",
                      "NEEDS_INPUT": "blocked"}.get(result.get("result"), task["status"])
    task["updated_at"] = now()
    save(root, state, tasks)
    log_event(root, "result_collected", task=a.id, state=result.get("result"),
              commit=result.get("commit"), changed=len(result.get("changed_files") or []),
              valid=verdict["valid"])
    out = {"task_id": a.id, "state": result.get("result"), "valid": verdict["valid"],
           "errors": verdict["errors"], "warnings": verdict["warnings"],
           "claimed_changed_files": result.get("changed_files"),
           "claimed_tests": result.get("tests"), "blockers": result.get("blockers"),
           "reminder": "a result report is a claim: run `verify` (git + scope) before trusting it"}
    if a.json:
        print(json.dumps(out, indent=2))
    else:
        print(f"RESULT: {result.get('result')}  task={a.id}  valid={verdict['valid']}")
        for e in verdict["errors"]:
            print(f"  error: {e}")
        for w in verdict["warnings"]:
            print(f"  warning: {w}")
        print(f"  claimed commit: {result.get('commit')}")
        print(f"  claimed changed files: {len(result.get('changed_files') or [])}")
        print(f"  {out['reminder']}")
    return 0 if verdict["valid"] else 1


def collect_verification(root, state, task, contract) -> dict:
    """Mechanical, independent verification of a task. Returns recorded evidence."""
    worktree = Path(task["worktree"]) if task.get("worktree") else Path(state["repo"]["root"])
    base = task.get("base_commit") or contract.get("base_commit") or state["repo"]["base_commit"]
    head = task.get("branch") or "HEAD"
    ev = {"worktree": str(worktree), "base": base, "head": head, "commands": [], "at": now()}
    if not worktree.is_dir():
        ev["error"] = f"worktree {worktree} does not exist"
        ev["worktree_clean"] = None
        return ev
    code, status = run(["git", "-C", str(worktree), "status", "--porcelain"])
    # Route through scope_guard so generated output (__pycache__, node_modules, build dirs) does not
    # read as dirty — two implementations of "clean" drifting apart is how a gate lies.
    ev["worktree_clean"] = SG.worktree_clean(worktree) if code == 0 else None
    ev["commands"].append({"command": f"git -C {worktree} status --porcelain", "exit_code": code,
                           "output": status[:400]})
    if base:
        code, log = run(["git", "-C", str(worktree), "log", "--oneline", f"{base}..{head}"])
        ev["commands"].append({"command": f"git -C {worktree} log --oneline {base}..{head}",
                               "exit_code": code, "output": log[:800]})
        ev["commits"] = [ln.split(" ", 1)[0] for ln in log.splitlines() if ln.strip()] if code == 0 else []
        code, names = run(["git", "-C", str(worktree), "diff", "--name-only", f"{base}...{head}"])
        ev["commands"].append({"command": f"git -C {worktree} diff --name-only {base}...{head}",
                               "exit_code": code, "output": names[:1200]})
        ev["changed_files"] = [p for p in names.splitlines() if p.strip()] if code == 0 else []
    else:
        ev["commits"], ev["changed_files"] = [], []
    commit = C.as_text(task.get("commit")) or (ev["commits"][0] if ev["commits"] else None)
    ev["commit"] = commit
    if commit:
        code, _ = run(["git", "-C", str(worktree), "cat-file", "-e", f"{commit}^{{commit}}"])
        ev["commit_exists"] = code == 0
        code, _ = run(["git", "-C", str(state["repo"]["integration_checkout"]), "merge-base",
                       "--is-ancestor", str(commit), "HEAD"])
        ev["commit_integrated"] = code == 0
    else:
        ev["commit_exists"] = False
        ev["commit_integrated"] = False
    if contract:
        ev["scope"] = SG.check_scope(contract, repo=worktree, base=base, head=head,
                                     include_dirty=False)
    else:
        ev["scope"] = {"status": "UNKNOWN", "error": "no contract to check the diff against"}
    unaccounted = set(ev.get("changed_files") or []) - set((ev["scope"].get("changed") or []))
    ev["unaccounted_paths"] = sorted(unaccounted)
    ev["ok"] = bool(ev.get("commit_exists") and ev.get("worktree_clean")
                    and ev["scope"].get("status") == "PASS" and not unaccounted)
    return ev


def cmd_verify(a) -> int:
    root = Path(a.repo_root).expanduser().resolve()
    d, state, tasks = load(root)
    task = find_task(tasks, a.id)
    if task is None:
        fail(f"unknown task {a.id!r}")
    contract = task_contract(task)
    ev = collect_verification(root, state, task, contract)
    task["verification"] = ev
    task["scope_validation"] = ev.get("scope")
    task["worktree_clean"] = ev.get("worktree_clean")
    task["changed_files"] = ev.get("changed_files") or []
    if ev.get("commit"):
        task["commit"] = ev["commit"]
    task["verified"] = bool(ev.get("ok"))
    task["last_activity"] = now()
    task["updated_at"] = now()
    save(root, state, tasks)
    scope_status = (ev.get("scope") or {}).get("status")
    log_event(root, "scope_checked", task=a.id, status=scope_status,
              changed=len(ev.get("changed_files") or []),
              violations=len(((ev.get("scope") or {}).get("violations")) or []))
    if scope_status == "FAIL":
        for violation in ((ev.get("scope") or {}).get("violations") or []):
            log_event(root, "scope_violation", task=a.id, path=violation.get("path"),
                      kind=violation.get("kind"), detail=violation.get("detail"))
    out = {"task_id": a.id, "verified": task["verified"], "commit": ev.get("commit"),
           "commit_exists": ev.get("commit_exists"), "commit_integrated": ev.get("commit_integrated"),
           "worktree": ev.get("worktree"), "worktree_clean": ev.get("worktree_clean"),
           "changed_files": ev.get("changed_files"), "unaccounted_paths": ev.get("unaccounted_paths"),
           "unexpected": (ev.get("scope") or {}).get("unexpected"),
           "forbidden": (ev.get("scope") or {}).get("forbidden"),
           "scope_status": scope_status, "error": ev.get("error"),
           "note": "diff bodies are not loaded into the orchestrator context: inspect them only "
                   "when this verdict is ambiguous"}
    if a.json:
        print(json.dumps(out, indent=2))
    else:
        print(f"VERIFY: {'OK' if task['verified'] else 'NOT OK'}  task={a.id}")
        print(f"  commit: {ev.get('commit')} exists={ev.get('commit_exists')} "
              f"already_integrated={ev.get('commit_integrated')}")
        print(f"  worktree: {ev.get('worktree')} clean={ev.get('worktree_clean')}")
        print(f"  changed: {len(ev.get('changed_files') or [])} path(s)  scope={scope_status}")
        if ev.get("unaccounted_paths"):
            print(f"  unaccounted: {', '.join(ev['unaccounted_paths'])}")
        for v in ((ev.get("scope") or {}).get("violations") or []):
            print(f"  VIOLATION [{v['kind']}] {v['path']}")
        if ev.get("error"):
            print(f"  error: {ev['error']}")
        print(f"  {out['note']}")
    return 0 if task["verified"] else 1


def cmd_validate_scope(a) -> int:
    root = Path(a.repo_root).expanduser().resolve()
    d, state, tasks = load(root)
    task = find_task(tasks, a.id)
    if task is None:
        fail(f"unknown task {a.id!r}")
    contract = task_contract(task)
    if not contract:
        fail(f"task {a.id!r} has no contract: SCOPE cannot be validated without one")
    worktree = Path(task["worktree"]) if task.get("worktree") else Path(state["repo"]["root"])
    result = SG.check_scope(contract, repo=worktree, base=a.base or contract.get("base_commit"),
                            head=a.head or task.get("branch"), include_dirty=a.include_dirty)
    if a.store:
        task["scope_validation"] = result
        task["updated_at"] = now()
        save(root, state, tasks)
    log_event(root, "scope_checked", task=a.id, status=result.get("status"),
              changed=len(result.get("changed") or []),
              violations=[v.get("path") for v in (result.get("violations") or [])][:20])
    for violation in result.get("violations") or []:
        log_event(root, "scope_violation", task=a.id, path=violation.get("path"),
                  kind=violation.get("kind"), detail=violation.get("detail"))
    if a.json:
        print(json.dumps(result, indent=2))
    else:
        print(SG.render_check(result))
    return 0 if result.get("status") == "PASS" else 1


def compute_gate(root, state, task, *, live: bool) -> dict:
    contract = task_contract(task)
    scope = task.get("scope_validation")
    worktree_clean = task.get("worktree_clean")
    commit_exists = bool(task.get("commit"))
    if live:
        ev = collect_verification(root, state, task, contract)
        task["verification"] = ev
        task["scope_validation"] = ev.get("scope")
        task["worktree_clean"] = ev.get("worktree_clean")
        task["changed_files"] = ev.get("changed_files") or []
        if ev.get("commit"):
            task["commit"] = ev["commit"]
        scope = task["scope_validation"]
        worktree_clean = task["worktree_clean"]
        commit_exists = bool(ev.get("commit_exists"))
    gate = C.merge_gate(task, verified_scope=scope, worktree_clean=worktree_clean,
                        commit_exists=commit_exists)
    task["merge_gate"] = gate
    task["updated_at"] = now()
    return gate


# ------------------------------------------------------------------- overlap (v1.4)
# Two live writers whose write scopes can match the same path are a merge conflict on a
# timer. Refuse (or serialise) before dispatch: exit 2 means "collision, do not dispatch".

TERMINAL_STATUSES = {"integrated", "cancelled"}


def _live_scope(d: Path, task: dict) -> list:
    """The scope a live task is actually writing: its contract's, else the plan's estimate."""
    cpath = d / "contracts" / f"{task['id']}.json"
    if cpath.exists():
        try:
            scope = json.loads(cpath.read_text(encoding="utf-8")).get("write_scope")
        except (OSError, ValueError):
            scope = None
        if scope:
            return list(scope)
    return list(task.get("expected_scope") or [])


def cmd_overlap(a) -> int:
    root = Path(a.repo_root).expanduser().resolve()
    d, state, tasks = load(root)
    live = []
    for t in tasks["tasks"]:
        if t["status"] in TERMINAL_STATUSES:
            continue
        scope = _live_scope(d, t)
        if scope:
            live.append({"task_id": t["id"], "status": t["status"], "write_scope": scope})
    collisions = SG.pairwise_overlaps(live)
    if a.json:
        print(json.dumps({
            "live_tasks": live,
            "collisions": collisions,
            "definite": [c for c in collisions if c["confidence"] == "definite"],
        }, indent=2))
    else:
        for c in collisions:
            print(f"COLLISION ({c['confidence']}): {c['tasks'][0]} vs {c['tasks'][1]}"
                  f"  ->  {c['patterns'][0]} / {c['patterns'][1]}")
        print("OVERLAP: NONE" if not collisions else f"OVERLAP: {len(collisions)} COLLISION(S)")
    if collisions:
        log_event(root, "scope_overlap_detected", count=len(collisions),
                  pairs=[c["tasks"] for c in collisions],
                  definite=sum(1 for c in collisions if c["confidence"] == "definite"))
        return 2
    return 0


def cmd_merge_gate(a) -> int:
    root = Path(a.repo_root).expanduser().resolve()
    d, state, tasks = load(root)
    task = find_task(tasks, a.id)
    if task is None:
        fail(f"unknown task {a.id!r}")
    gate = compute_gate(root, state, task, live=a.live)
    save(root, state, tasks)
    log_event(root, "merge_gate_evaluated", task=a.id, ready=gate["ready"],
              reasons=gate["reasons"])
    if a.json:
        print(json.dumps(gate, indent=2))
    else:
        print(C.render_merge_gate(gate))
        if not gate["ready"]:
            print()
            print("ready: false means DO NOT MERGE. Return the work to the responsible worker "
                  "(or record an explicit, logged escalation).")
    return 0 if gate["ready"] else 1


def cmd_guard(a) -> int:
    """Install/plan/verify the run-owned guards for a task's worker (Layer A)."""
    root = Path(a.repo_root).expanduser().resolve()
    d, state, tasks = load(root)
    task = find_task(tasks, a.id)
    if task is None:
        fail(f"unknown task {a.id!r}")
    contract = task_contract(task)
    if not contract:
        fail(f"task {a.id!r} has no contract: guards are generated from the contract")
    recorded = a.worktree or task.get("worktree")
    if not recorded and a.install_hook:
        fail(f"task {a.id!r} has no worktree recorded: a scope gate installed on the shared "
             f"checkout would be a false prevention claim. Record it first "
             f"(`set-task --id {a.id} --worktree <path>`) or pass --worktree explicitly.")
    worktree = Path(recorded or state["repo"]["root"]).expanduser().resolve()
    kind = a.kind or (task.get("worker_execution") or {}).get("kind") \
        or task.get("preferred_agent_kind") or "auto"
    out = {"task_id": a.id, "kind": kind, "worktree": str(worktree)}
    rc = 0
    if a.install_hook or not (a.plan or a.verify_launch):
        installed = SG.install_hook(contract, worktree, root)
        out["hook"] = installed
        if installed.get("installed"):
            log_event(root, "scope_guard_installed", task=a.id, worktree=str(worktree),
                      mechanism=installed.get("mechanism"),
                      shared_config=installed.get("shared_config_touched"))
        else:
            log_event(root, "scope_guard_unavailable", task=a.id, worktree=str(worktree),
                      reason=installed.get("error"))
            rc = 1
    if a.plan:
        out["prevention_plan"] = SG.plan_prevention(
            contract, kind, out_dir=root / ".orchestrator" / "guards" / a.id)
        if out["prevention_plan"]["prevention"] == "none":
            log_event(root, "scope_guard_unavailable", task=a.id, kind=kind,
                      reason="no verified write-boundary mechanism")
    if a.verify_launch:
        verified = SG.verify_launch(contract, kind, cwd=a.cwd or str(worktree), observed=a.observed)
        out["launch_verification"] = verified
        log_event(root, "launch_verified" if verified["verified"] else "scope_guard_unavailable",
                  task=a.id, kind=kind, mechanism=verified.get("mechanism"),
                  reasons=verified.get("reasons"))
        if not verified["verified"]:
            rc = 1
    print(json.dumps(out, indent=2))
    return rc


def cmd_checkpoint(a) -> int:
    """Persist a worker checkpoint. Checkpoints are for long tasks; they live in .orchestrator/."""
    root = Path(a.repo_root).expanduser().resolve()
    d, state, tasks = load(root)
    task = find_task(tasks, a.id)
    if task is None:
        fail(f"unknown task {a.id!r}")
    path = d / "checkpoints" / f"{a.id}.json"
    if a.list:
        entries = sorted(p.name for p in (d / "checkpoints").glob("*.json"))
        history = d / "checkpoints" / f"{a.id}.history.jsonl"
        print(json.dumps({"checkpoints": entries, "this_task_history":
                          len(history.read_text(encoding="utf-8").splitlines()) if history.exists() else 0},
                         indent=2))
        return 0
    if a.show or not (a.set or a.file or a.text):
        if not path.exists():
            fail(f"no checkpoint recorded for task {a.id!r}")
        data = read_json(path)
        if a.json:
            print(json.dumps(data, indent=2))
        else:
            print(C.render_checkpoint(data))
        return 0

    if a.file and a.file != "-":
        try:
            raw = C.load_structured_text(Path(a.file).expanduser().read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            fail(f"cannot read checkpoint file: {exc}")
        if not isinstance(raw, dict):
            fail("checkpoint file is not a mapping")
    elif a.file == "-":
        raw = C.load_structured_text(sys.stdin.read())
    elif a.text:
        raw = C.load_structured_text(a.text)
    else:
        previous = read_json(path) if path.exists() else {}
        raw = {"phase": a.phase if a.phase is not None else previous.get("phase", 0),
               "total_phases": a.total_phases if a.total_phases is not None
               else previous.get("total_phases", 0),
               "completed": a.completed or previous.get("completed", []),
               "current": a.current or previous.get("current", []),
               "remaining": a.remaining or previous.get("remaining", []),
               "decisions": a.decision or previous.get("decisions", []),
               "blockers": a.blocker or previous.get("blockers", []),
               "last_known_commit": a.commit or previous.get("last_known_commit")}
    if isinstance(raw, dict) and isinstance(raw.get("checkpoint"), dict) and len(raw) == 1:
        raw = raw["checkpoint"]          # the documented `checkpoint:` wrapper shape
    cp = C.normalize_checkpoint(raw, a.id)
    if a.worker:
        cp["worker"] = a.worker
    elif not cp.get("worker"):
        cp["worker"] = task.get("agent")
    if a.commit:
        cp["last_known_commit"] = a.commit
    verdict = C.validate_checkpoint(cp)
    if not verdict["valid"]:
        for e in verdict["errors"]:
            print(f"CHECKPOINT_INVALID: {e}", file=sys.stderr)
        return 2
    cp["updated_at"] = now()
    previous = read_json(path) if path.exists() else None
    if previous:
        with open(d / "checkpoints" / f"{a.id}.history.jsonl", "a", encoding="utf-8") as fh:
            fh.write(json.dumps({**previous, "superseded_at": now()}) + "\n")
    atomic_write(path, json.dumps(cp, indent=2) + "\n")
    task["checkpoint"] = {"path": str(path), "phase": cp["phase"], "total_phases": cp["total_phases"],
                          "completed": len(cp["completed"]), "remaining": cp["remaining"],
                          "blockers": cp["blockers"], "updated_at": cp["updated_at"],
                          "last_known_commit": cp.get("last_known_commit")}
    task["last_activity"] = now()
    task["updated_at"] = now()
    save(root, state, tasks)
    log_event(root, "checkpoint_created", task=a.id, phase=cp["phase"],
              total_phases=cp["total_phases"], remaining=len(cp["remaining"]),
              commit=cp.get("last_known_commit"), worker=cp.get("worker"))
    print(json.dumps(cp, indent=2) if a.json else C.render_checkpoint(cp))
    return 0


def cmd_replace_worker(a) -> int:
    """Record a worker replacement and print the reconstruction the new worker must receive."""
    root = Path(a.repo_root).expanduser().resolve()
    d, state, tasks = load(root)
    task = find_task(tasks, a.id)
    if task is None:
        fail(f"unknown task {a.id!r}")
    contract = task_contract(task)
    if not contract:
        fail(f"task {a.id!r} has no contract: a replacement worker cannot be given a scope")

    previous = task.get("current_worker") or {}
    old_agent = a.old_agent or previous.get("agent") or task.get("agent")
    live_agents = {}
    if not a.no_herdr:
        code, payload = run(["herdr", "agent", "list"])
        if code == 0:
            try:
                for ag in json.loads(payload).get("result", {}).get("agents", []):
                    if ag.get("name"):
                        live_agents[ag["name"]] = ag
            except ValueError:
                live_agents = {}
    blocking = [name for name in (old_agent, a.agent) if name in live_agents
                and name != a.agent]
    if blocking and not a.force:
        fail(f"refusing to replace: {', '.join(blocking)} is still live — two writers in one "
             f"worktree corrupt each other. Stop the old worker first, or re-run with --force "
             f"(which is recorded as a decision).")

    cp = None
    cp_path = d / "checkpoints" / f"{a.id}.json"
    if cp_path.exists():
        cp = read_json(cp_path)
    task.setdefault("worker_history", []).append({
        "agent": old_agent, "pane": previous.get("pane") or task.get("pane"),
        "workspace": previous.get("workspace") or task.get("workspace"),
        "kind": (task.get("worker_execution") or {}).get("kind"),
        "replaced_at": now(), "reason": a.reason,
        "last_checkpoint_phase": (cp or {}).get("phase"),
        "last_commit": (cp or {}).get("last_known_commit") or task.get("commit"),
        "live_at_replacement": bool(old_agent in live_agents),
    })
    task["replacement_count"] = int(task.get("replacement_count") or 0) + 1
    task["current_worker"] = {"agent": a.agent, "pane": a.pane or task.get("pane"),
                             "workspace": a.workspace or task.get("workspace"),
                             "since": now(), "replacement": task["replacement_count"]}
    task["agent"] = a.agent
    if a.pane:
        task["pane"] = a.pane
    if a.workspace:
        task["workspace"] = a.workspace
    task["status"] = "dispatched"
    task["updated_at"] = now()
    save(root, state, tasks)
    for kind, val in (("owned_agents", a.agent), ("owned_panes", a.pane),
                      ("owned_workspaces", a.workspace)):
        if val and val not in state["resources"][kind]:
            state["resources"][kind].append(val)
    save(root, state, tasks)
    log_event(root, "worker_replaced", task=a.id, old_agent=old_agent, agent=a.agent,
              reason=a.reason, replacement_count=task["replacement_count"],
              live_at_replacement=bool(old_agent in live_agents))

    ev = collect_verification(root, state, task, contract)
    task["verification"] = ev
    task["scope_validation"] = ev.get("scope")
    save(root, state, tasks)

    lines = ["WORKER REPLACEMENT — reconstructed state (send this to the new worker; do NOT just "
             "say 'continue where the other one stopped').", "",
             f"task: {a.id}   previous worker: {old_agent or '-'}   new worker: {a.agent}",
             f"replacement #: {task['replacement_count']}   reason: {a.reason or '-'}", "",
             "TASK CONTRACT (unchanged):", C.render_contract(contract), "",
             "CURRENT WORKTREE / BRANCH:",
             f"- worktree: {ev.get('worktree')}",
             f"- branch: {task.get('branch')}   base: {ev.get('base')}",
             f"- worktree clean: {ev.get('worktree_clean')}",
             f"- commits on the branch since base: {', '.join(ev.get('commits') or []) or 'none'}",
             f"- recorded commit: {ev.get('commit')} (exists: {ev.get('commit_exists')})",
             f"- changed files: {', '.join(ev.get('changed_files') or []) or 'none'}",
             f"- scope: {((ev.get('scope') or {}).get('status'))} "
             f"(violations: {len(((ev.get('scope') or {}).get('violations')) or [])})", ""]
    if cp:
        lines += ["LATEST CHECKPOINT (trust it only after re-checking the worktree):",
                  C.render_checkpoint(cp), ""]
    else:
        lines += ["LATEST CHECKPOINT: none recorded — reconstruct the remaining work from Git "
                  "(diff + commits above) and say explicitly what you verified yourself.", ""]
    lines += ["REMAINING WORK:",
              "- " + "; ".join((cp or {}).get("remaining") or []) if (cp or {}).get("remaining")
              else "- derive it from the contract's acceptance criteria and the diff",
              "",
              "RULES: we are already at replacement #{n}. One writer per worktree — the previous "
              "worker must not be running. Do not redo completed work, do not widen the scope, "
              "commit your own work, and report with the standard result contract.".format(
                  n=task["replacement_count"])]
    if task.get("verdict"):
        lines += ["", f"EXISTING REVIEW VERDICT: {task['verdict']}"]
    if task.get("notes"):
        lines += ["", "FINDINGS / NOTES SO FAR:"] + [f"- {n['note']}" for n in task["notes"][-5:]]
    package = "\n".join(lines)
    out_path = d / "reports" / f"{a.id}-replacement-{task['replacement_count']}.txt"
    atomic_write(out_path, package + "\n")
    print(package)
    print(f"\n(written to {out_path})")
    return 0


def cmd_events(a) -> int:
    root = Path(a.repo_root).expanduser().resolve()
    require_state(root)
    events = events_mod.read_events(root)
    if a.task:
        events = [e for e in events if e.get("task") == a.task or e.get("task_id") == a.task]
    if a.kind:
        events = [e for e in events if e.get("event") in set(a.kind)]
    if a.since:
        events = [e for e in events if str(e.get("time", "")) >= a.since]
    events = events[-a.tail:] if a.tail else events
    if a.json:
        print(json.dumps(events, indent=2))
    else:
        for rec in events:
            line = f"{rec.get('time')}  {rec.get('event'):<24} {rec.get('task') or '-':<20}"
            extras = {k: v for k, v in rec.items()
                      if k not in ("time", "event", "task", "task_id", "run_id")}
            print(line + ("  " + json.dumps(extras)[:160] if extras else ""))
    return 0


def cmd_set_task(a) -> int:
    root = Path(a.repo_root).expanduser().resolve()
    d, state, tasks = load(root)
    task = next((t for t in tasks["tasks"] if t["id"] == a.id), None)
    if task is None:
        fail(f"unknown task {a.id!r}")
    if a.status and a.status not in STATUSES:
        fail(f"invalid status {a.status!r}: {', '.join(STATUSES)}")
    if a.launch_mode and a.launch_mode not in WORKER_EXECUTION_MODES:
        fail(f"invalid --launch-mode {a.launch_mode!r}: {', '.join(WORKER_EXECUTION_MODES)}")

    # status transitions that the contract gate must approve
    if a.status == "ready":
        verdict = contract_verdict(task)
        if not verdict["valid"] and not a.force:
            fail(f"TASK_CONTRACT_INVALID: task {a.id!r} cannot become ready — first error: "
                 f"{verdict['errors'][0] if verdict['errors'] else 'unknown'}")
        if not verdict["valid"]:
            log_event(root, "task_direct_override", task=a.id, what="ready without a valid contract",
                      reason=a.note or "no reason given")
            decide(root, f"task {a.id} forced ready without a valid contract: "
                         f"{a.note or 'no reason given'}")
    if a.status == "integrated":
        gate = compute_gate(root, state, task, live=False)
        if not gate["ready"] and not a.force:
            fail("MERGE GATE NOT READY: " + ", ".join(gate["reasons"]) +
                 " — fix the task or run `merge-gate --live`; `--force` requires an explicit, "
                 "recorded reason")
        if not gate["ready"]:
            log_event(root, "merge_gate_bypassed", task=a.id, reasons=gate["reasons"],
                      reason=a.note or "no reason given")
            decide(root, f"merge gate BYPASSED for task {a.id}: {', '.join(gate['reasons'])} — "
                         f"{a.note or 'no reason given'}")

    changed = []
    for field in ("status", "agent", "workspace", "pane", "worktree", "branch", "base_commit",
                  "commit", "verdict", "report"):
        val = getattr(a, field, None)
        if val is not None:
            task[field] = val
            changed.append(field)
    if a.verified is not None:
        task["verified"] = bool(a.verified)
        changed.append("verified")
    if a.worktree_clean is not None:
        task["worktree_clean"] = bool(a.worktree_clean)
        changed.append("worktree_clean")
    if a.tests_status:
        task["tests"] = {"status": a.tests_status, "at": now(),
                         "command": a.tests_command, "evidence": a.tests_evidence}
        changed.append("tests")
        log_event(root, {"pass": "test_passed", "fail": "test_failed", "started": "test_started"}
                  .get(a.tests_status, "test_started"), task=a.id, status=a.tests_status,
                  command=a.tests_command)
    if a.blocker:
        task.setdefault("blockers", [])
        for b in a.blocker:
            if b not in task["blockers"]:
                task["blockers"].append(b)
        changed.append("blocker")
    if a.clear_blockers:
        task["blockers"] = []
        changed.append("clear_blockers")
    if a.fix_cycles_open is not None:
        task["fix_cycles_open"] = a.fix_cycles_open
        changed.append("fix_cycles_open")
        if a.fix_cycles_open:
            log_event(root, "fix_cycle_started", task=a.id, open=a.fix_cycles_open)
        else:
            log_event(root, "fix_cycle_closed", task=a.id)

    # worker execution (launch) record
    launch = task.get("worker_execution") or {"mode": None, "kind": None, "args": [],
                                             "verified_after_spawn": None}
    if a.launch_mode is not None:
        launch["mode"] = a.launch_mode
        changed.append("launch_mode")
    if a.launch_kind is not None:
        launch["kind"] = a.launch_kind
        changed.append("launch_kind")
    if a.launch_arg:
        launch["args"] = list(a.launch_arg)
        changed.append("launch_args")
    if a.launch_verified is not None:
        launch["verified_after_spawn"] = bool(a.launch_verified)
        changed.append("launch_verified")
    if any(launch.get(k) for k in ("mode", "kind", "args", "verified_after_spawn")):
        task["worker_execution"] = launch

    if a.note:
        task["notes"].append({"time": now(), "note": a.note})
        changed.append("note")
    task["last_activity"] = now()
    task["updated_at"] = now()
    if task.get("agent") and not task.get("current_worker"):
        task["current_worker"] = {"agent": task["agent"], "pane": task.get("pane"),
                                  "workspace": task.get("workspace"), "since": now()}

    # ownership ledger
    for kind, val in (("owned_agents", a.agent), ("owned_workspaces", a.workspace),
                      ("owned_panes", a.pane), ("owned_worktrees", a.worktree),
                      ("owned_branches", a.branch)):
        if val and val not in state["resources"][kind]:
            state["resources"][kind].append(val)
    if a.status:
        if a.status == "integrated":
            if task["id"] not in state["integration"]["completed"]:
                state["integration"]["completed"].append(task["id"])
            log_event(root, "merged", task=task["id"], commit=task.get("commit"))
        elif a.status in ("passed",):
            if task["id"] not in state["integration"]["pending"]:
                state["integration"]["pending"].append(task["id"])
    save(root, state, tasks)
    log_event(root, "task_updated", task=task["id"], changed=changed, status=task["status"],
              commit=task["commit"])
    print(json.dumps({k: task[k] for k in ("id", "status", "agent", "worktree", "branch", "commit",
                                          "worker_execution")}, indent=2))
    return 0


def cmd_event(a) -> int:
    root = Path(a.repo_root).expanduser().resolve()
    require_state(root)
    known = set(events_mod.EVENT_KINDS)
    if a.event not in known and not a.allow_unknown:
        fail(f"unknown event {a.event!r}: add it to scripts/events.py EVENT_KINDS, or pass "
             f"--allow-unknown (known: {len(known)} kinds)")
    data = dict(kv.split("=", 1) for kv in a.data) if a.data else {}
    log_event(root, a.event, task=a.task, **data)
    print(f"logged {a.event}" + (f" ({a.task})" if a.task else ""))
    return 0


def cmd_ready(a) -> int:
    root = Path(a.repo_root).expanduser().resolve()
    d, state, tasks = load(root)
    done = {t["id"] for t in tasks["tasks"] if t["status"] in DEP_SATISFIED}
    blocked_by_contract = []
    ready = []
    for t in tasks["tasks"]:
        if t["status"] not in ("pending", "ready"):
            continue
        if not all(dep in done for dep in t["depends_on"]):
            continue
        verdict = contract_verdict(t)
        if t.get("mutates_files") and not verdict["valid"]:
            blocked_by_contract.append((t["id"], verdict["errors"][:1]))
            continue
        ready.append(t)
    for t in ready:
        print(f"{t['id']}\t{t['role']}\tmutates={int(t['mutates_files'])}\t{t['title']}")
    if not ready:
        print("(no ready tasks)")
    for tid, errs in blocked_by_contract:
        print(f"TASK_CONTRACT_INVALID\t{tid}\t{errs[0] if errs else 'invalid contract'}")
    return 0


def cmd_status(a) -> int:
    root = Path(a.repo_root).expanduser().resolve()
    d, state, tasks = load(root)
    if a.json:
        print(json.dumps({"state": state, "tasks": tasks}, indent=2))
        return 0
    print(f"run {state['run_id']}  status={state['status']}  repo={state['repo']['root']}")
    print(f"base {state['repo']['base_branch']}@{state['repo']['base_commit']}  "
          f"integration={state['repo']['integration_checkout']}")
    tc = state["team_constraints"]
    print(f"modes: coordination={state['coordination_mode']} team={state['team_mode']} "
          f"workers={state['worker_execution_mode']} "
          f"kinds={tc['allowed_agent_kinds'] or 'any'}"
          + (f" pins={tc['pinned_roles']}" if tc["pinned_roles"] else ""))
    print()
    hdr = (f"{'task':<20} {'role':<11} {'status':<11} {'agent':<18} {'scope':<6} {'gate':<6} "
           f"{'branch':<26} commit")
    print(hdr)
    print("-" * len(hdr))
    for t in tasks["tasks"]:
        scope = (t.get("scope_validation") or {}).get("status") or "-"
        gate = "ready" if (t.get("merge_gate") or {}).get("ready") else \
            ("no" if t.get("merge_gate") else "-")
        print(f"{t['id'][:20]:<20} {t['role'][:11]:<11} {t['status'][:11]:<11} "
              f"{(t['agent'] or '-')[:18]:<18} {scope[:6]:<6} {gate[:6]:<6} "
              f"{(t['branch'] or '-')[:26]:<26} {(t['commit'] or '-')[:12]}")
    owned = state["resources"]
    print()
    print(f"owned: agents={len(owned['owned_agents'])} workspaces={len(owned['owned_workspaces'])} "
          f"panes={len(owned['owned_panes'])} worktrees={len(owned['owned_worktrees'])} "
          f"branches={len(owned['owned_branches'])}")
    cp_dir = d / "checkpoints"
    if cp_dir.is_dir() and any(cp_dir.glob("*.json")):
        print("checkpoints: " + ", ".join(sorted(p.stem for p in cp_dir.glob("*.json"))))
    return 0


def cmd_reconcile(a) -> int:
    """Read-only. Prints only discrepancies between persisted state and reality."""
    root = Path(a.repo_root).expanduser().resolve()
    d, state, tasks = load(root)
    problems = []

    # --- Herdr runtime
    agents = {}
    if not a.no_herdr:
        code, out = run(["herdr", "agent", "list"])
        if code != 0:
            problems.append(f"HERDR: `herdr agent list` failed ({out[:120]}) — runtime unverified")
        else:
            try:
                payload = json.loads(out)
                for ag in payload.get("result", {}).get("agents", []):
                    if ag.get("name"):
                        agents[ag["name"]] = ag
            except json.JSONDecodeError:
                problems.append("HERDR: could not parse `herdr agent list` output")

    for t in tasks["tasks"]:
        tid = t["id"]
        if t["agent"] and not a.no_herdr:
            live = agents.get(t["agent"])
            if live is None and t["status"] in ("dispatched", "working", "blocked"):
                problems.append(f"TASK {tid}: persisted status={t['status']} but agent {t['agent']!r} "
                                f"is gone from the runtime -> interrupted (see `checkpoint` and "
                                f"`replace-worker`)")
            elif live is not None and t["status"] in ("dispatched", "working"):
                if live.get("agent_status") in ("idle", "done") and not t["commit"]:
                    problems.append(f"TASK {tid}: agent {t['agent']!r} is {live.get('agent_status')} "
                                    f"with no recorded commit -> inspect and collect")
                elif live.get("agent_status") == "blocked":
                    problems.append(f"TASK {tid}: agent {t['agent']!r} is blocked -> classify and "
                                    f"resolve with the user if it needs approval")
        if t["worktree"]:
            wt = Path(t["worktree"])
            if not wt.is_dir():
                problems.append(f"TASK {tid}: recorded worktree {wt} is missing -> stale resource")
            else:
                code, br = run(["git", "-C", str(wt), "branch", "--show-current"])
                if code == 0 and t["branch"] and br != t["branch"]:
                    problems.append(f"TASK {tid}: worktree branch is {br!r}, state says {t['branch']!r}")
                code, st = run(["git", "-C", str(wt), "status", "--porcelain",
                                "--untracked-files=all"])
                paths = []
                for ln in (st or "").splitlines():
                    chunk = ln[3:].strip()
                    if " -> " in chunk:
                        chunk = chunk.split(" -> ", 1)[1]
                    if chunk:
                        pn = chunk.strip('"')
                        if not SG.matches_any(pn, SG.ALWAYS_IGNORED):   # generated output is not dirt
                            paths.append(pn)
                if code == 0 and paths:
                    problems.append(f"TASK {tid}: worktree has uncommitted changes ({len(paths)} paths)")
                    contract = task_contract(t)
                    if contract:
                        cls = SG.classify_paths(paths, contract)
                        if cls["violations"]:
                            problems.append(f"TASK {tid}: uncommitted SCOPE_VIOLATION "
                                            f"({', '.join(v['path'] for v in cls['violations'][:5])})")
        if t["commit"]:
            code, _ = run(["git", "-C", state["repo"]["integration_checkout"],
                           "merge-base", "--is-ancestor", t["commit"], "HEAD"])
            if code == 0 and t["status"] != "integrated":
                problems.append(f"TASK {tid}: commit {t['commit'][:9]} is already reachable from HEAD -> "
                                f"integrated")
        if t.get("mutates_files") and not t.get("contract"):
            problems.append(f"TASK {tid}: mutating task without a contract -> cannot be delegated "
                            f"safely (run `contract`)")
        elif t.get("contract"):
            verdict = contract_verdict(t)
            if not verdict["valid"]:
                problems.append(f"TASK {tid}: contract invalid ({verdict['errors'][0]})")
        cp = d / "checkpoints" / f"{tid}.json"
        if cp.exists() and t["status"] in ("dispatched", "working"):
            data = read_json(cp)
            if data.get("last_known_commit") and t.get("commit") and \
                    data["last_known_commit"] != t["commit"]:
                problems.append(f"TASK {tid}: checkpoint commit {str(data['last_known_commit'])[:9]} "
                                f"differs from recorded commit {str(t['commit'])[:9]}")

    for kind, label in (("owned_workspaces", "workspace"), ("owned_worktrees", "worktree"),
                        ("owned_panes", "pane")):
        for res in state["resources"][kind]:
            if kind == "owned_worktrees" and res and not Path(res).is_dir():
                problems.append(f"RESOURCE {label} {res}: path missing -> stale")
            if kind == "owned_workspaces" and not a.no_herdr and not any(
                    ag.get("workspace_id") == res for ag in agents.values()):
                problems.append(f"RESOURCE {label} {res}: no live agent in it (may be an empty "
                                f"workspace this run owns)")

    if problems:
        print(f"{len(problems)} discrepancy(ies):")
        for p in problems:
            print(f"  - {p}")
        print("\nReconcile by hand (Git/Herdr reality wins over state), then update with `set-task`.")
        return 1
    print("no discrepancies between persisted state and Git/Herdr reality")
    return 0


def cmd_validate(a) -> int:
    root = Path(a.repo_root).expanduser().resolve()
    d, state, tasks = load(root)
    errs = []
    warns = []
    for key in ("version", "run_id", "status", "repo", "resources", "tasks"):
        if key not in state:
            errs.append(f"state.json missing key {key!r}")

    raw = read_json(d / "state.json")
    missing_modes = [k for k in MODE_KEYS if k not in raw]
    if missing_modes:
        warns.append(f"legacy state.json missing {', '.join(missing_modes)} — defaults assumed "
                     f"({DEFAULT_COORDINATION_MODE}/{DEFAULT_TEAM_MODE}/{DEFAULT_WORKER_EXECUTION_MODE}); "
                     f"run `set-modes` to persist")
    if raw.get("version") != STATE_VERSION:
        warns.append(f"state.json version {raw.get('version')} != {STATE_VERSION}: it is migrated in "
                     f"memory on read and persisted on the next write (contracts/checkpoints/gates "
                     f"default to empty, nothing is dropped)")
    if "watchdog" not in raw:
        warns.append("state.json has no watchdog thresholds block — defaults assumed "
                     "(stall_after=900s)")

    if state["coordination_mode"] not in COORDINATION_MODES:
        errs.append(f"invalid coordination_mode {state['coordination_mode']!r}: {COORDINATION_MODES}")
    if state["team_mode"] not in TEAM_MODES:
        errs.append(f"invalid team_mode {state['team_mode']!r}: {TEAM_MODES}")
    if state["worker_execution_mode"] not in WORKER_EXECUTION_MODES:
        errs.append(f"invalid worker_execution_mode {state['worker_execution_mode']!r}: "
                    f"{WORKER_EXECUTION_MODES}")
    tc = state["team_constraints"]
    for key in ("allowed_agent_kinds", "pinned_roles", "max_workers", "notes"):
        if key not in tc:
            errs.append(f"team_constraints missing key {key!r}")
        elif key in ("allowed_agent_kinds", "notes") and not isinstance(tc[key], list):
            errs.append(f"team_constraints.{key} must be a list")
        elif key == "pinned_roles" and not isinstance(tc[key], dict):
            errs.append("team_constraints.pinned_roles must be an object")

    seen = set()
    for t in tasks["tasks"]:
        if t["id"] in seen:
            errs.append(f"duplicate task id {t['id']!r}")
        seen.add(t["id"])
        if t["status"] not in STATUSES:
            errs.append(f"task {t['id']}: unknown status {t['status']!r}")
        if t["role"] not in ROLES:
            errs.append(f"task {t['id']}: unknown role {t['role']!r}")
        if not t["acceptance"]:
            errs.append(f"task {t['id']}: no acceptance criteria (unverifiable task)")
        if t["mutates_files"] and not t["worktree_required"]:
            errs.append(f"task {t['id']}: mutates files but no worktree required")
        if t.get("mutates_files"):
            verdict = contract_verdict(t)
            if not verdict["valid"]:
                severity = "err" if t["status"] in ("ready", "dispatched", "working", "blocked",
                                                    "review", "needs_fix", "passed") else "warn"
                msg = (f"task {t['id']}: contract invalid "
                       f"({'; '.join(verdict['errors'][:3]) or 'missing contract'})")
                (errs if severity == "err" else warns).append(msg)
            for w in verdict["warnings"][:2]:
                warns.append(f"task {t['id']}: {w}")
        cp = t.get("checkpoint")
        if cp and cp.get("blockers") and t["status"] in ("passed", "integrated"):
            errs.append(f"task {t['id']}: status {t['status']} with unresolved checkpoint blockers "
                        f"({'; '.join(cp['blockers'][:2])})")
        if t.get("merge_gate") and t["status"] == "integrated" and not t["merge_gate"].get("ready"):
            errs.append(f"task {t['id']}: integrated with a merge gate that is not ready "
                        f"({', '.join(t['merge_gate'].get('reasons') or [])})")
        launch = t.get("worker_execution")
        if launch:
            if launch.get("mode") and launch["mode"] not in WORKER_EXECUTION_MODES:
                errs.append(f"task {t['id']}: invalid launch mode {launch['mode']!r}")
            if launch.get("mode") == "autonomous" and launch.get("verified_after_spawn") is False:
                errs.append(f"task {t['id']}: autonomous launch not verified after spawn "
                            f"(record --launch-verified 1 once argv was checked)")
        if int(t.get("replacement_count") or 0) > 0 and not t.get("worker_history"):
            errs.append(f"task {t['id']}: replacement_count > 0 without worker_history")
    for t in tasks["tasks"]:
        for dep in t["depends_on"]:
            if dep not in seen:
                errs.append(f"task {t['id']}: depends on unknown task {dep!r}")
    if not a.no_herdr:
        code, out = run(["herdr", "agent", "list"])
        if code != 0:
            errs.append("herdr agent list failed — runtime not verified")
    for w in warns:
        print(f"WARNING: {w}")
    if errs:
        for e in errs:
            print(f"INVALID: {e}")
        return 1
    print(f"state valid: run {state['run_id']}, {len(tasks['tasks'])} task(s), status {state['status']}, "
          f"coordination={state['coordination_mode']}, team={state['team_mode']}, "
          f"workers={state['worker_execution_mode']}, state v{STATE_VERSION}")
    return 0


def proposal_count(d: Path) -> int:
    path = d / "skill-proposals.md"
    if not path.exists():
        return 0
    return sum(1 for ln in path.read_text(encoding="utf-8").splitlines() if ln.startswith("## ["))


def cmd_report(a) -> int:
    root = Path(a.repo_root).expanduser().resolve()
    d, state, tasks = load(root)
    if a.result:
        state["status"] = a.result.lower()
        save(root, state, tasks)
        log_event(root, "run_finished", result=state["status"])
    if a.pause:
        state["status"] = "paused"
        save(root, state, tasks)
        log_event(root, "run_paused")
    if a.cancel:
        state["status"] = "cancelled"
        save(root, state, tasks)
        log_event(root, "run_cancelled")
        for t in tasks["tasks"]:
            if t["status"] not in ("integrated", "passed", "cancelled", "failed"):
                print(f"still active: {t['id']} (agent={t['agent']}, worktree={t['worktree']})")
    tc = state["team_constraints"]
    lines = [
        f"RESULT: {state['status'].upper()}",
        "",
        f"run: {state['run_id']}",
        f"repo: {state['repo']['root']}  base: {state['repo']['base_branch']}@{state['repo']['base_commit']}",
        "",
        "Run configuration:",
        f"- coordination_mode: {state['coordination_mode']}",
        f"- team_mode: {state['team_mode']}",
        f"- worker_execution_mode: {state['worker_execution_mode']}",
        f"- allowed_agent_kinds: {tc['allowed_agent_kinds'] or 'any installed kind'}",
        f"- pinned_roles: {tc['pinned_roles'] or 'none'}",
        f"- max_workers: {tc['max_workers'] if tc['max_workers'] is not None else 'unbounded'}",
        f"- watchdog.stall_after: {state.get('watchdog', {}).get('stall_after')}s",
        "",
        "Tasks:",
    ]
    for t in tasks["tasks"]:
        launch = t.get("worker_execution") or {}
        launch_txt = ""
        if launch.get("mode"):
            launch_txt = f" launch={launch.get('kind') or '?'} {' '.join(launch.get('args') or [])} "\
                         f"verified={bool(launch.get('verified_after_spawn'))}"
        contract = t.get("contract") or {}
        lines.append(f"- {t['id']}: {t['status']}" + (f" ({t['commit'][:9]})" if t["commit"] else "")
                     + (f" verdict={t['verdict']}" if t["verdict"] else "") + launch_txt
                     + (f" contract={t.get('contract_digest')}" if contract else " contract=MISSING"))
    lines += ["", "Contracts and scope:"]
    for t in tasks["tasks"]:
        contract = t.get("contract") or {}
        scope = t.get("scope_validation") or {}
        lines.append(f"- {t['id']}: contract={'pass' if contract and contract_verdict(t)['valid'] else 'fail'}"
                     f" digest={t.get('contract_digest') or '-'} write_scope={len(contract.get('write_scope') or [])}"
                     f" scope={scope.get('status') or 'not checked'}"
                     f" violations={len(scope.get('violations') or [])}")
    lines += ["", "Merge gates:"]
    gates = [t for t in tasks["tasks"] if t.get("merge_gate")]
    lines += [f"- {t['id']}: ready={t['merge_gate']['ready']} "
              f"({', '.join(t['merge_gate'].get('reasons') or []) or 'all fields pass'})" for t in gates] \
        or ["- no gate evaluated"]
    lines += ["", "Checkpoints:"]
    cps = [t for t in tasks["tasks"] if t.get("checkpoint")]
    lines += [f"- {t['id']}: phase {t['checkpoint'].get('phase')}/{t['checkpoint'].get('total_phases')} "
              f"remaining={len(t['checkpoint'].get('remaining') or [])} "
              f"blockers={len(t['checkpoint'].get('blockers') or [])}" for t in cps] or ["- none"]
    lines += ["", "Worker replacements:"]
    reps = [t for t in tasks["tasks"] if int(t.get("replacement_count") or 0) > 0]
    lines += [f"- {t['id']}: {t['replacement_count']} replacement(s); last reason: "
              f"{(t.get('worker_history') or [{}])[-1].get('reason') or '-'}" for t in reps] or ["- none"]
    lines += ["", "Integrated commits:"]
    integrated = [t for t in tasks["tasks"] if t["status"] == "integrated"]
    lines += [f"- {t['id']}: {t['commit']}" for t in integrated] or ["- none"]
    lines += ["", "Verified in this run:"]
    lines += [f"- {t['id']}: verified={bool(t['verified'])} scope={((t.get('scope_validation') or {}).get('status')) or 'n/a'}"  # noqa: E501
              for t in tasks["tasks"]] or ["- none"]
    lines += ["", "Outstanding risks:"]
    lines += [f"- {t['id']}: " + "; ".join(n["note"] for n in t["notes"][-2:])
              for t in tasks["tasks"] if t["notes"]] or ["- none recorded"]
    lines += ["", "Resources remaining:"]
    owned = state["resources"]
    remaining = (owned["owned_agents"] + owned["owned_workspaces"] + owned["owned_panes"]
                 + owned["owned_worktrees"] + owned["owned_branches"])
    lines += [f"- {r}" for r in remaining] or ["- none"]
    n_prop = proposal_count(d)
    lines += ["", f"Skill proposals recorded: {n_prop}" +
              (" (see .orchestrator/skill-proposals.md; the skill was NOT modified)" if n_prop else "")]
    lines += ["", "Cleanup performed: see events.jsonl (cleanup_* events) and decisions.md"]
    text = "\n".join(lines) + "\n"
    out = Path(a.out).expanduser() if a.out else d / "reports" / f"run-report-{state['run_id']}.txt"
    out.parent.mkdir(parents=True, exist_ok=True)
    atomic_write(out, text)
    print(text)
    print(f"(written to {out})")
    return 0


def cmd_review_package(a) -> int:
    """Serialize exactly what the independent reviewer must judge, against the same contract.

    The reviewer receives the contract, not a paraphrase: base commit, worker commit, changed files,
    scope validation, acceptance criteria and the test evidence, plus the read-only instruction and
    the required structured verdict.
    """
    root = Path(a.repo_root).expanduser().resolve()
    d, state, tasks = load(root)
    task = find_task(tasks, a.id)
    if task is None:
        fail(f"unknown task {a.id!r}")
    contract = task_contract(task)
    if not contract:
        fail(f"task {a.id!r} has no contract: a review without the original contract is not "
             f"independent review, it is opinion")
    ev = task.get("verification")
    if a.live or not ev:
        ev = collect_verification(root, state, task, contract)
        task["verification"] = ev
        task["scope_validation"] = ev.get("scope")
        task["worktree_clean"] = ev.get("worktree_clean")
        if ev.get("commit"):
            task["commit"] = ev["commit"]
        save(root, state, tasks)
    scope = ev.get("scope") or {}
    tests = task.get("tests") or {}
    lines = [
        "REVIEW PACKAGE — you are an INDEPENDENT, READ-ONLY reviewer.",
        "Judge the work against the task contract below, not against the worker's summary.",
        "",
        "TASK CONTRACT (the yardstick; the worker must not have changed it):",
        C.render_contract(contract),
        "",
        "WHAT TO INSPECT (verify yourself; never take the worker's word):",
        f"- worktree: {ev.get('worktree')}",
        f"- base commit: {ev.get('base')}",
        f"- branch: {task.get('branch')}   worker commit: {ev.get('commit')} "
        f"(exists: {ev.get('commit_exists')}, already integrated: {ev.get('commit_integrated')})",
        f"- worktree clean: {ev.get('worktree_clean')}",
        f"- changed files ({len(ev.get('changed_files') or [])}):",
    ]
    lines += [f"    {p}" for p in (ev.get("changed_files") or [])] or ["    (none)"]
    lines += [
        f"- scope validation: {scope.get('status')} "
        f"(unexpected: {len(scope.get('unexpected') or [])}, "
        f"forbidden: {len(scope.get('forbidden') or [])})",
        f"- unaccounted paths (in git but not in the scope diff): "
        f"{', '.join(ev.get('unaccounted_paths') or []) or 'none'}",
        "",
        "ACCEPTANCE CRITERIA — judge each one explicitly:",
    ]
    lines += [f"- {c}: PASS | FAIL" for c in (contract.get("acceptance_criteria") or [])] or ["- none"]
    lines += [
        "",
        "REQUIRED CHECKS the contract asks for / the worker claims:",
    ]
    for check in contract.get("required_checks") or []:
        lines.append(f"- {check}")
    lines.append(f"- observed test evidence: {tests.get('status') or 'none recorded'} "
                 f"(command: {tests.get('command') or '-'}, evidence: {tests.get('evidence') or '-'})")
    lines += [
        "",
        "VERIFY INDEPENDENTLY: CORRECTNESS, SCOPE, ACCEPTANCE, REGRESSIONS, UNRELATED_CHANGES.",
        "Do not edit, format, commit or fix anything: a FAIL goes back to the responsible worker.",
        "",
        "Return exactly this shape:",
        "verdict: PASS | FAIL",
        "blocking_findings: []      (actionable, referenced to file/behaviour; required when FAIL)",
        "non_blocking_notes: []",
        "scope_findings: []",
        "acceptance:",
    ]
    for criterion in (contract.get("acceptance_criteria") or []):
        lines.append(f"  {criterion}: PASS | FAIL")
    lines += ["", "A FAIL without actionable findings is not usable: state the specifics."]
    package = "\n".join(lines)
    out_path = d / "reports" / f"{a.id}-review-package.txt"
    atomic_write(out_path, package + "\n")
    task["review_package"] = {"path": str(out_path), "at": now()}
    task["updated_at"] = now()
    save(root, state, tasks)
    log_event(root, "review_started", task=a.id, package=str(out_path),
              scope=scope.get("status"), commit=ev.get("commit"))
    print(package)
    print(f"\n(written to {out_path})")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Orchestrator state manager (.orchestrator/)")
    p.add_argument("--repo-root", default=".", help="repository/workspace root (default: cwd)")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("init")
    s.add_argument("--run-id")
    s.add_argument("--slug")
    s.add_argument("--base-branch")
    s.add_argument("--base-commit")
    s.add_argument("--integration-checkout")
    s.add_argument("--orchestrator-name", default=os.environ.get("HERMES_AGENT_NAME", "hermes"))
    s.add_argument("--workspace", default=os.environ.get("HERDR_WORKSPACE_ID"))
    s.add_argument("--pane", default=os.environ.get("HERDR_PANE_ID"))
    s.add_argument("--coordination-mode", choices=COORDINATION_MODES, default=DEFAULT_COORDINATION_MODE)
    s.add_argument("--team-mode", choices=TEAM_MODES, default=DEFAULT_TEAM_MODE)
    s.add_argument("--worker-execution-mode", choices=WORKER_EXECUTION_MODES,
                   default=DEFAULT_WORKER_EXECUTION_MODE)
    s.add_argument("--allowed-agent-kind", action="append", default=[],
                   help="agent kind the team may use (repeatable; empty = any installed kind)")
    s.add_argument("--pin", action="append", default=[],
                   help="ROLE=KIND or TASK_ID=KIND composition constraint (repeatable)")
    s.add_argument("--max-workers", type=int, default=None, help="0 = unbounded")
    s.add_argument("--stall-after", type=int, default=DEFAULT_WATCHDOG["stall_after"],
                   help="watchdog: seconds without activity before a worker counts as stalled")
    s.add_argument("--constraint-note")
    s.add_argument("--force", action="store_true")
    s.set_defaults(func=cmd_init)

    s = sub.add_parser("set-modes")
    s.add_argument("--coordination-mode", choices=COORDINATION_MODES)
    s.add_argument("--team-mode", choices=TEAM_MODES)
    s.add_argument("--worker-execution-mode", choices=WORKER_EXECUTION_MODES)
    s.add_argument("--allowed-agent-kind", action="append", help="replace the allowed-kind list")
    s.add_argument("--clear-allowed-kinds", action="store_true")
    s.add_argument("--pin", action="append", help="ROLE=KIND or TASK_ID=KIND")
    s.add_argument("--unpin", action="append", help="ROLE or TASK_ID")
    s.add_argument("--max-workers", type=int, help="0 = unbounded")
    s.add_argument("--stall-after", type=int, help="watchdog stall threshold in seconds")
    s.add_argument("--clear-constraints", action="store_true")
    s.add_argument("--note", help="why the change was made (recorded in decisions.md)")
    s.set_defaults(func=cmd_set_modes)

    s = sub.add_parser("modes")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_modes)

    s = sub.add_parser("propose")
    s.add_argument("--kind", default="pitfall", choices=PROPOSAL_KINDS)
    s.add_argument("--title", required=True)
    s.add_argument("--detail")
    s.add_argument("--task")
    s.add_argument("--proposal-status", default="proposed",
                   choices=["proposed", "applied", "rejected"])
    s.set_defaults(func=cmd_propose)

    s = sub.add_parser("add-task")
    s.add_argument("--id", required=True)
    s.add_argument("--title", required=True)
    s.add_argument("--role", default="worker", choices=ROLES)
    s.add_argument("--mutates", type=int, default=1, help="1 if the task writes files")
    s.add_argument("--scope", action="append", default=[], help="allowed path/component (repeatable)")
    s.add_argument("--acceptance", action="append", default=[], help="measurable criterion (repeatable)")
    s.add_argument("--depends-on", action="append", default=[], help="task id (repeatable)")
    s.add_argument("--preferred-agent", default="auto")
    s.add_argument("--worktree-required", default=None)
    s.set_defaults(func=cmd_add_task)

    s = sub.add_parser("set-task")
    s.add_argument("--id", required=True)
    s.add_argument("--status", choices=STATUSES)
    s.add_argument("--agent")
    s.add_argument("--workspace")
    s.add_argument("--pane")
    s.add_argument("--worktree")
    s.add_argument("--branch")
    s.add_argument("--base-commit")
    s.add_argument("--commit")
    s.add_argument("--verdict")
    s.add_argument("--report")
    s.add_argument("--verified", type=int, help="1/0 — orchestrator-side independent verification")
    s.add_argument("--worktree-clean", type=int, help="1/0 — observed worktree state (merge gate)")
    s.add_argument("--tests-status", choices=["started", "pass", "fail"])
    s.add_argument("--tests-command")
    s.add_argument("--tests-evidence", help="where the observed test output was captured")
    s.add_argument("--blocker", action="append", help="record an unresolved blocker (repeatable)")
    s.add_argument("--clear-blockers", action="store_true")
    s.add_argument("--fix-cycles-open", type=int, help="0 = the fix loop is closed")
    s.add_argument("--force", action="store_true",
                   help="override a contract/gate refusal (recorded in decisions.md)")
    s.add_argument("--launch-mode", choices=WORKER_EXECUTION_MODES,
                   help="worker_execution_mode this worker was launched with")
    s.add_argument("--launch-kind", help="agent kind the worker was started as")
    s.add_argument("--launch-arg", action="append",
                   help="extra argv passed to the agent after `--` (repeatable); for values starting "
                        "with a dash use --launch-arg=--flag")
    s.add_argument("--launch-verified", type=int, help="1/0 — observed argv checked after spawn")
    s.add_argument("--note")
    s.set_defaults(func=cmd_set_task)

    s = sub.add_parser("contract")
    s.add_argument("--id", required=True)
    s.add_argument("--file", help="contract file (JSON, or the YAML subset used in prompts)")
    s.add_argument("--show", action="store_true", help="print the stored contract and its verdict")
    s.add_argument("--role", choices=ROLES)
    s.add_argument("--objective", action="append")
    s.add_argument("--write-scope", action="append")
    s.add_argument("--read-scope", action="append")
    s.add_argument("--forbidden-scope", action="append")
    s.add_argument("--acceptance", action="append")
    s.add_argument("--required-check", action="append")
    s.add_argument("--deliverable", action="append")
    s.add_argument("--phase-plan", action="append")
    s.add_argument("--depends-on", action="append")
    s.add_argument("--when-blocked")
    s.add_argument("--mutation-policy", choices=C.MUTATION_POLICIES)
    s.add_argument("--checkpoint-policy", choices=C.CHECKPOINT_POLICIES)
    s.add_argument("--scope-justification")
    s.add_argument("--agent-kind")
    s.add_argument("--worker")
    s.add_argument("--note", action="append")
    s.add_argument("--base-commit")
    s.add_argument("--branch")
    s.add_argument("--worktree")
    s.add_argument("--model", help="pinned model for this task (never inherited from the session)")
    s.add_argument("--budget-tokens", help="hard token ceiling for this task")
    s.add_argument("--budget-usd", help="hard cost ceiling for this task")
    s.add_argument("--force", action="store_true", help="allow a material contract change")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_contract)

    s = sub.add_parser("resume", help="diagnose (and optionally rebuild) a run whose worktree vanished")
    s.add_argument("--id", required=True)
    s.add_argument("--recreate", action="store_true",
                   help="git worktree add the recorded branch at the canonical run path")
    s.add_argument("--path", help="explicit worktree path (default: recorded one, else the run path)")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_resume)

    s = sub.add_parser("result")
    s.add_argument("--id", required=True)
    s.add_argument("--file", help="worker result report (JSON or the key/value shape); '-' = stdin")
    s.add_argument("--text", help="inline result report")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_result)

    s = sub.add_parser("verify")
    s.add_argument("--id", required=True)
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_verify)

    s = sub.add_parser("validate-scope")
    s.add_argument("--id", required=True)
    s.add_argument("--base")
    s.add_argument("--head")
    s.add_argument("--include-dirty", action="store_true")
    s.add_argument("--no-store", dest="store", action="store_false", default=True)
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_validate_scope)

    s = sub.add_parser("overlap", help="refuse live tasks whose write scopes collide "
                                       "(exit 2 = collision, do not dispatch)")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_overlap)

    s = sub.add_parser("merge-gate")
    s.add_argument("--id", required=True)
    s.add_argument("--live", action="store_true", help="refresh git/scope observations first")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_merge_gate)

    s = sub.add_parser("guard")
    s.add_argument("--id", required=True)
    s.add_argument("--kind", help="worker kind (default: the recorded launch kind)")
    s.add_argument("--worktree")
    s.add_argument("--install-hook", action="store_true", help="install the pre-commit scope gate")
    s.add_argument("--plan", action="store_true", help="generate the per-kind prevention artifacts")
    s.add_argument("--verify-launch", action="store_true", help="prove the prevention is in force")
    s.add_argument("--observed", help="environment value captured from the worker's shell")
    s.add_argument("--cwd")
    s.set_defaults(func=cmd_guard)

    s = sub.add_parser("checkpoint")
    s.add_argument("--id", required=True)
    s.add_argument("--set", action="store_true")
    s.add_argument("--file", help="checkpoint file (JSON/YAML subset) or '-' for stdin")
    s.add_argument("--text", help="inline checkpoint")
    s.add_argument("--show", action="store_true")
    s.add_argument("--list", action="store_true")
    s.add_argument("--phase", type=int)
    s.add_argument("--total-phases", type=int)
    s.add_argument("--completed", action="append")
    s.add_argument("--current", action="append")
    s.add_argument("--remaining", action="append")
    s.add_argument("--decision", action="append")
    s.add_argument("--blocker", action="append")
    s.add_argument("--commit")
    s.add_argument("--worker")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_checkpoint)

    s = sub.add_parser("replace-worker")
    s.add_argument("--id", required=True)
    s.add_argument("--agent", required=True, help="the new worker's agent name")
    s.add_argument("--old-agent")
    s.add_argument("--pane")
    s.add_argument("--workspace")
    s.add_argument("--reason")
    s.add_argument("--force", action="store_true",
                   help="replace even if the previous agent still looks live (recorded)")
    s.add_argument("--no-herdr", action="store_true")
    s.set_defaults(func=cmd_replace_worker)

    s = sub.add_parser("review-package")
    s.add_argument("--id", required=True)
    s.add_argument("--live", action="store_true", help="refresh git/scope observations first")
    s.set_defaults(func=cmd_review_package)

    s = sub.add_parser("events")
    s.add_argument("--task")
    s.add_argument("--kind", action="append", help="event name (repeatable)")
    s.add_argument("--since", help="ISO timestamp lower bound")
    s.add_argument("--tail", type=int, default=40)
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_events)

    s = sub.add_parser("event")
    s.add_argument("--event", required=True)
    s.add_argument("--task")
    s.add_argument("--data", action="append", default=[], help="key=value (repeatable)")
    s.add_argument("--allow-unknown", action="store_true")
    s.set_defaults(func=cmd_event)

    s = sub.add_parser("ready")
    s.set_defaults(func=cmd_ready)

    s = sub.add_parser("status")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_status)

    s = sub.add_parser("reconcile")
    s.add_argument("--no-herdr", action="store_true", help="Git/filesystem checks only")
    s.set_defaults(func=cmd_reconcile)

    s = sub.add_parser("validate")
    s.add_argument("--no-herdr", action="store_true")
    s.set_defaults(func=cmd_validate)

    s = sub.add_parser("report")
    s.add_argument("--result", choices=["success", "partial", "failed"])
    s.add_argument("--pause", action="store_true")
    s.add_argument("--cancel", action="store_true")
    s.add_argument("--out")
    s.set_defaults(func=cmd_report)

    a = p.parse_args()
    return a.func(a)


if __name__ == "__main__":
    sys.exit(main())
