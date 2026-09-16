#!/usr/bin/env python3
"""Deterministic runtime watchdog. stdlib only.

Separation of concerns, on purpose:

    WATCHDOG  = mechanical observation, classification, event persistence, alerting
    HERMES    = decisions, architecture, contracts, review, integration

The watchdog never writes code, never integrates branches, never answers trust/credential/sudo
prompts, never kills a worker and never decides architecture. It samples the run, classifies each
task from *combined* signals, appends structured events and prints a compact report. A stalled
or spinning task is a prompt to inspect - never an order to kill - and "spinning" is the case that
matters most for a chatty worker: output moving for a long time with no file change and no commit.
classification is a prompt for the orchestrator to inspect - not an order to kill anything.

Signals combined per task (nothing decisive on a single timeout):

    herdr agent state (working/blocked/idle/done/unknown/missing)
    agent output hash (did the terminal output change since the previous sample?)
    process liveness of the pane (foreground argv, when herdr can report it)
    pane / workspace existence
    worktree existence, HEAD commit time, uncommitted paths
    checkpoint file mtime, last event time for the task
    time since the last observed activity

Sampling sources are injectable (`--fixture FILE` or `--no-herdr`) so the classification logic is
unit-testable without a live Herdr server and without a real multi-agent run.

Classifications: healthy, working, idle, done, blocked, stalled, spinning, process_dead, agent_gone,
pane_missing, workspace_missing, worktree_missing, unknown.

Exit codes: 0 everything healthy, 1 at least one task needs attention, 2 usage error.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from contracts import normalize_contract  # noqa: E402
from events import log_event, read_events  # noqa: E402

try:  # scope classification reuses the single scope implementation
    from scope_guard import classify_paths
except Exception:  # pragma: no cover - scope module is always present in the skill
    classify_paths = None

ACTIVE_STATUSES = {"dispatched", "working", "blocked", "review"}
DEFAULT_STALL_AFTER = 900        # seconds without any observed activity before "stalled"
DEFAULT_DEAD_GRACE = 60          # seconds a recorded agent may be missing before "agent_gone"
DEFAULT_IDLE_GRACE = 60          # seconds idle with no commit before it is worth flagging
DEFAULT_SPIN_AFTER = 1800        # seconds of visible activity with ZERO file change/commit -> "spinning"
MIN_INTERVAL = 5
WATCHDOG_DIR = Path(".orchestrator") / "watchdog"


def now_ts() -> float:
    return time.time()


def iso(ts: float | None) -> str | None:
    if not ts:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc).astimezone().isoformat(timespec="seconds")


def parse_iso(text: str | None) -> float | None:
    if not text:
        return None
    try:
        return datetime.fromisoformat(str(text).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def run_cli(cmd: list, timeout: int = 20) -> tuple[int, str]:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return proc.returncode, (proc.stdout or proc.stderr).strip()
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 127, str(exc)


def git(path, args: list) -> tuple[int, str]:
    return run_cli(["git", "-C", str(path), *args], timeout=30)


# --------------------------------------------------------------------------- runtime snapshot

def _result_of(payload):
    if isinstance(payload, dict):
        body = payload.get("result", payload)
        return body if isinstance(body, dict) else {}
    return {}


def runtime_snapshot(*, fixture: str | None = None, use_herdr: bool = True) -> dict:
    """Read Herdr reality once. Tolerant: unknown/missing fields become None, never an exception."""
    snap = {"available": False, "source": None, "error": None, "agents": {}, "panes": set(),
            "workspaces": set(), "process_info": {}, "captured_at": iso(now_ts())}
    if fixture:
        try:
            payload = json.loads(Path(fixture).read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            snap["error"] = f"fixture unreadable: {exc}"
            return snap
        snap["available"] = True
        snap["source"] = f"fixture:{fixture}"
        _ingest(snap, payload)
        return snap
    if not use_herdr:
        snap["error"] = "herdr inspection disabled (--no-herdr)"
        return snap
    code, out = run_cli(["herdr", "agent", "list"])
    if code != 0:
        snap["error"] = f"`herdr agent list` failed: {out[:160]}"
        return snap
    try:
        _ingest(snap, {"agent_list": json.loads(out)})
    except ValueError:
        snap["error"] = "`herdr agent list` output is not JSON"
        return snap
    snap["available"] = True
    snap["source"] = "herdr"
    code, out = run_cli(["herdr", "pane", "list"])
    if code == 0:
        try:
            for pane in _result_of(json.loads(out)).get("panes", []) or []:
                if pane.get("pane_id"):
                    snap["panes"].add(pane["pane_id"])
        except ValueError:
            pass
    code, out = run_cli(["herdr", "workspace", "list"])
    if code == 0:
        try:
            for ws in _result_of(json.loads(out)).get("workspaces", []) or []:
                if ws.get("workspace_id"):
                    snap["workspaces"].add(ws["workspace_id"])
        except ValueError:
            pass
    return snap


def _ingest(snap: dict, payload: dict) -> None:
    """Accept either a live payload shape or the fixture shape (same keys)."""
    agents_payload = payload.get("agent_list") or payload.get("agents") or payload
    if isinstance(agents_payload, list):
        entries = agents_payload
    else:
        entries = _result_of(agents_payload).get("agents", []) or []
    for entry in entries:
        name = entry.get("name")
        if not name:
            continue
        snap["agents"][name] = {
            "agent": entry.get("agent"),
            "status": entry.get("agent_status"),
            "pane": entry.get("pane_id"),
            "workspace": entry.get("workspace_id"),
            "cwd": entry.get("cwd"),
            "foreground_cwd": entry.get("foreground_cwd"),
            "terminal_id": entry.get("terminal_id"),
        }
    for pane in (payload.get("panes") or []):
        pid = pane.get("pane_id") if isinstance(pane, dict) else pane
        if pid:
            snap["panes"].add(pid)
    for ws in (payload.get("workspaces") or []):
        wid = ws.get("workspace_id") if isinstance(ws, dict) else ws
        if wid:
            snap["workspaces"].add(wid)
    for pane_id, info in (payload.get("process_info") or {}).items():
        snap["process_info"][pane_id] = info


def pane_process_argv(snap: dict, pane_id: str | None, *, use_herdr: bool,
                      fixture: str | None) -> tuple[list | None, str]:
    """Foreground argv of a pane, when observable. Returns (argv, how)."""
    if not pane_id:
        return None, "no-pane-recorded"
    if fixture:
        info = snap["process_info"].get(pane_id)
        if info is None:
            return None, "fixture-missing"
        if isinstance(info, dict):
            procs = info.get("foreground_processes") or info.get("processes") or []
            argv = procs[0].get("argv") if procs and isinstance(procs[0], dict) else info.get("argv")
        else:
            argv = info
        return (list(argv) if argv else None), "fixture"
    if not use_herdr:
        return None, "herdr-disabled"
    code, out = run_cli(["herdr", "pane", "process-info", "--pane", pane_id])
    if code != 0:
        return None, f"process-info-failed:{out[:80]}"
    try:
        body = _result_of(json.loads(out))
    except ValueError:
        return None, "process-info-unparsable"
    procs = body.get("foreground_processes") or body.get("processes") or []
    argv = procs[0].get("argv") if procs and isinstance(procs[0], dict) else None
    return (list(argv) if argv else None), "herdr"


def agent_output_hash(snap: dict, name: str, *, use_herdr: bool, fixture: str | None) -> str | None:
    """Hash of the agent's recent output. Identical hash across samples == no new output."""
    if fixture:
        return None
    if not use_herdr:
        return None
    code, out = run_cli(["herdr", "agent", "read", name, "--source", "recent-unwrapped", "--lines",
                         "60"], timeout=30)
    if code != 0:
        return None
    return hashlib.sha256(out.encode("utf-8", "replace")).hexdigest()[:16]


# --------------------------------------------------------------------------- task sampling

def load_state(root: Path) -> tuple[dict, list]:
    base = root / ".orchestrator"
    try:
        state = json.loads((base / "state.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        state = {}
    try:
        tasks = json.loads((base / "tasks.json").read_text(encoding="utf-8")).get("tasks", [])
    except (OSError, ValueError):
        tasks = []
    return state, tasks


def load_contract(root: Path, task: dict) -> dict | None:
    if isinstance(task.get("contract"), dict) and task["contract"]:
        return normalize_contract(task["contract"])
    base = root / ".orchestrator" / "contracts" / str(task.get("id"))
    for suffix in (".json", ".yaml", ".yml"):
        candidate = base.with_suffix(suffix)
        if candidate.is_file():
            try:
                from scope_guard import load_contract_file
                return load_contract_file(candidate)
            except Exception:  # noqa: BLE001 - a broken contract must not stop the watchdog
                return None
    return None


def last_commit_ts(worktree: Path) -> float | None:
    code, out = git(worktree, ["log", "-1", "--format=%ct"])
    if code != 0 or not out.strip().isdigit():
        return None
    return float(out.strip())


def checkpoint_ts(root: Path, task_id: str) -> float | None:
    path = root / ".orchestrator" / "checkpoints" / f"{task_id}.json"
    try:
        return path.stat().st_mtime
    except OSError:
        return None


def worktree_path_mtime(path: Path) -> float | None:
    best = None
    for base, dirs, files in os.walk(path):
        if ".git" in dirs:
            dirs.remove(".git")
        for name in files:
            try:
                ts = (Path(base) / name).stat().st_mtime
            except OSError:
                continue
            if best is None or ts > best:
                best = ts
    return best


def sample_task(root: Path, task: dict, snap: dict, prev: dict | None, *, use_herdr: bool,
                fixture: str | None, thresholds: dict, events: list) -> dict:
    tid = str(task.get("id"))
    status = str(task.get("status") or "unknown")
    agent = task.get("agent")
    pane = task.get("pane")
    worktree = Path(task["worktree"]) if task.get("worktree") else None
    out = {
        "task_id": tid, "status": status, "role": task.get("role"), "agent": agent, "pane": pane,
        "workspace": task.get("workspace"), "branch": task.get("branch"),
        "agent_state": None, "classification": "unknown", "signals": {}, "reasons": [],
        "last_activity": None, "seconds_since_activity": None, "scope_violation": None,
        "recoverable": None,
    }
    if status not in ACTIVE_STATUSES and status not in ("needs_fix", "ready"):
        out["classification"] = "inactive"
        return out

    signals = out["signals"]
    live = snap["agents"].get(agent) if agent else None
    signals["herdr_available"] = snap["available"]
    signals["agent_present"] = bool(live)
    signals["agent_state"] = live.get("status") if live else None
    signals["pane_present"] = (pane in snap["panes"]) if (pane and snap["panes"]) else None
    signals["workspace_present"] = ((task.get("workspace") in snap["workspaces"])
                                    if (task.get("workspace") and snap["workspaces"]) else None)
    signals["worktree_exists"] = worktree.is_dir() if worktree else None

    activity = []
    if worktree and worktree.is_dir():
        cts = last_commit_ts(worktree)
        signals["last_commit_ts"] = iso(cts)
        if cts:
            activity.append(cts)
        mts = worktree_path_mtime(worktree)
        signals["worktree_mtime"] = iso(mts)
        if mts:
            activity.append(mts)
        dirty = git(worktree, ["status", "--porcelain", "--untracked-files=all"])
        if dirty[0] == 0:
            paths = [ln[3:].strip().strip('"') for ln in dirty[1].splitlines() if ln.strip()]
            signals["uncommitted_paths"] = len(paths)
            if paths:
                write_ts = None
                for rel in paths[:50]:
                    try:
                        write_ts = max(write_ts or 0, (worktree / rel).stat().st_mtime)
                    except OSError:
                        continue
                if write_ts:
                    signals["last_write_ts"] = iso(write_ts)
                    activity.append(write_ts)
            contract = load_contract(root, task)
            if contract and paths and classify_paths is not None:
                cls = classify_paths(paths, contract)
                if cls["violations"]:
                    out["scope_violation"] = cls["violations"]
                    signals["uncommitted_out_of_scope"] = [v["path"] for v in cls["violations"]]
    # Produtividade: um worker que conversa sem tocar arquivo nenhum não está entregando.
    write_floor = None
    for cand in (signals.get("last_write_ts"), signals.get("last_commit_ts")):
        ts = parse_iso(cand)
        if ts:
            write_floor = max(write_floor or ts, ts)
    if write_floor is None:
        started = parse_iso((task.get("created_at") or task.get("dispatched_at")))
        write_floor = started
    signals["last_write_ts"] = signals.get("last_write_ts") or iso(write_floor)
    out["seconds_since_write"] = int(now_ts() - write_floor) if write_floor else None
    cts = checkpoint_ts(root, tid)
    signals["checkpoint_ts"] = iso(cts)
    if cts:
        activity.append(cts)
    ev = [e for e in events if e.get("task") == tid or e.get("task_id") == tid]
    last_event_ts = None
    for rec in ev[-5:]:
        ts = parse_iso(rec.get("time"))
        if ts:
            last_event_ts = max(last_event_ts or ts, ts)
    signals["last_event_ts"] = iso(last_event_ts)
    if not activity and last_event_ts:
        # orchestrator-side events are bookkeeping, not worker activity: they only provide a floor
        # for a task that has no worktree signal at all.
        activity.append(last_event_ts)

    argv, how = pane_process_argv(snap, pane, use_herdr=use_herdr, fixture=fixture)
    signals["process_info"] = how
    signals["process_argv"] = argv
    kind = ((task.get("worker_execution") or {}).get("kind")
            or task.get("preferred_agent_kind") or task.get("agent_kind"))
    if argv and kind and str(kind) != "auto":
        signals["process_matches_kind"] = any(str(kind) in str(a) for a in argv)
    else:
        signals["process_matches_kind"] = None

    state_name = signals["agent_state"]
    last = max(activity) if activity else None
    out["last_activity"] = iso(last)
    out["seconds_since_activity"] = int(now_ts() - last) if last else None
    if live:
        h = agent_output_hash(snap, agent, use_herdr=use_herdr, fixture=fixture)
        signals["output_hash"] = h
        prev_hash = ((prev or {}).get("signals") or {}).get("output_hash")
        if h and prev_hash and h != prev_hash:
            signals["output_changed"] = True
            prev_seen = parse_iso((prev or {}).get("captured_at")) or now_ts()
            activity.append(prev_seen if prev_seen > (last or 0) else now_ts())
        else:
            signals["output_changed"] = False

    # ------------------------------------------------------------------ classification
    cls = None
    if worktree and not worktree.is_dir():
        cls, why = "worktree_missing", "recorded worktree path does not exist -> the writer's tree is gone"
    elif signals["pane_present"] is False:
        cls, why = "pane_missing", "recorded pane is absent from the runtime"
    elif signals["workspace_present"] is False:
        cls, why = "workspace_missing", "recorded workspace is absent from the runtime"
    elif agent and not live and snap["available"]:
        cls, why = "agent_gone", "recorded agent is not in `herdr agent list` -> worker interrupted"
    elif live and signals["process_matches_kind"] is False:
        cls, why = "process_dead", "pane foreground process is not the worker CLI -> the agent process died"
    elif state_name == "blocked":
        cls, why = "blocked", "agent sits at an approval/question dialog: decision point, not completion"
    elif state_name in ("idle", "done"):
        if task.get("commit"):
            cls, why = "done", "agent is idle and a commit is recorded: collect and verify"
        else:
            cls, why = "idle", "agent is idle with no commit: inspect before concluding anything"
    elif out["scope_violation"]:
        cls, why = "scope_violation", "uncommitted changes outside write_scope/inside forbidden_scope"
    elif last is None:
        cls, why = "unknown", "no activity signal available at all (filesystem timestamps and agent output all unreadable)"
    elif out["seconds_since_activity"] is not None and out["seconds_since_activity"] > thresholds["stall_after"]:
        if (prev or {}).get("classification") in ("stalled", "working", "healthy"):
            cls, why = "stalled", (f"no commit/checkpoint/output change for "
                                   f"{out['seconds_since_activity']}s (threshold "
                                   f"{thresholds['stall_after']}s) while the agent claims to be working")
        else:
            cls, why = "working", "within the stall threshold"
    elif (state_name == "working" and signals.get("output_changed")
          and out.get("seconds_since_write") is not None
          and out["seconds_since_write"] > thresholds["spin_after"]
          and not signals.get("uncommitted_paths")):
        cls, why = "spinning", (f"{out['seconds_since_write']}s of visible activity with zero file "
                                f"change and no commit (threshold {thresholds['spin_after']}s): the "
                                f"worker is reading/measuring, not delivering -> inspect, then narrow "
                                f"the contract or replace the worker")
    else:
        cls, why = "healthy", "recent activity observed and no blocking signal"
    if cls in (None, "unknown") and out["scope_violation"]:
        cls = "scope_violation"
    out["classification"] = cls
    out["why"] = why
    out["recoverable"] = bool(worktree and worktree.is_dir() and (task.get("branch") or cts
                                                                or last_commit_ts(worktree))) \
        if cls in ("agent_gone", "process_dead", "stalled", "worktree_missing") else None
    if cls in ("agent_gone", "process_dead", "stalled", "pane_missing", "workspace_missing",
               "worktree_missing"):
        out["reasons"].append(why)
    out["captured_at"] = iso(now_ts())
    return out


# --------------------------------------------------------------------------- main sample

def sample(root: Path, *, use_herdr: bool = True, fixture: str | None = None,
           thresholds: dict | None = None, persist: bool = True) -> dict:
    root = Path(root).expanduser().resolve()
    state, tasks = load_state(root)
    limits = {"stall_after": DEFAULT_STALL_AFTER, "dead_grace": DEFAULT_DEAD_GRACE,
              "idle_grace": DEFAULT_IDLE_GRACE, "spin_after": DEFAULT_SPIN_AFTER}
    limits.update({k: v for k, v in (state.get("watchdog") or {}).items() if isinstance(v, int)})
    limits.update(thresholds or {})
    events = read_events(root)
    snap = runtime_snapshot(fixture=fixture, use_herdr=use_herdr)
    prev_path = root / WATCHDOG_DIR / "last_sample.json"
    try:
        prev = json.loads(prev_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        prev = None
    prev_by_task = {t.get("task_id"): t for t in ((prev or {}).get("tasks") or [])}

    rows = []
    for task in tasks:
        if str(task.get("status")) not in ACTIVE_STATUSES and str(task.get("status")) not in ("needs_fix", "ready"):
            continue
        rows.append(sample_task(root, task, snap, prev_by_task.get(str(task.get("id"))),
                                use_herdr=use_herdr, fixture=fixture, thresholds=limits,
                                events=events))

    needs_attention = [r for r in rows if r["classification"] in
                       ("blocked", "stalled", "spinning", "process_dead", "agent_gone", "pane_missing",
                        "workspace_missing", "worktree_missing", "scope_violation")]
    report = {
        "run_id": state.get("run_id"),
        "repo": str(root),
        "captured_at": iso(now_ts()),
        "herdr": {"available": snap["available"], "source": snap["source"], "error": snap["error"]},
        "thresholds": limits,
        "tasks": rows,
        "counts": {},
        "verdict": "healthy",
        "needs_attention": [r["task_id"] for r in needs_attention],
        "advisory": ("observation only: the watchdog does not decide, integrate, kill or answer "
                     "prompts — the orchestrator inspects and acts"),
    }
    for row in rows:
        report["counts"][row["classification"]] = report["counts"].get(row["classification"], 0) + 1
    if not snap["available"]:
        report["verdict"] = "degraded"
    elif needs_attention:
        report["verdict"] = "attention"

    if persist:
        out_dir = root / WATCHDOG_DIR
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "last_sample.json").write_text(json.dumps(report, indent=2) + "\n",
                                                  encoding="utf-8")
        log_event(root, "watchdog_sample", details={
            "verdict": report["verdict"], "counts": report["counts"],
            "needs_attention": report["needs_attention"]})
        if not snap["available"]:
            log_event(root, "watchdog_degraded", reason=snap["error"] or "herdr unavailable")
        for row in rows:
            prev_cls = (prev_by_task.get(row["task_id"]) or {}).get("classification")
            if row["classification"] == prev_cls:
                continue
            mapping = {"stalled": "worker_stalled", "spinning": "worker_spinning",
                       "blocked": "worker_blocked",
                       "agent_gone": "worker_failed", "process_dead": "worker_failed",
                       "worktree_missing": "worker_failed", "pane_missing": "worker_failed",
                       "workspace_missing": "worker_failed"}
            if row["classification"] == "scope_violation":
                # one event per offending path: the audit trail must name the files
                for violation in row.get("scope_violation") or []:
                    log_event(root, "scope_violation", task=row["task_id"], agent=row["agent"],
                              pane=row["pane"], branch=row["branch"],
                              path=violation.get("path"), kind=violation.get("kind"),
                              detail=violation.get("detail"),
                              details={"source": "watchdog", "uncommitted": True})
            if row["classification"] in mapping:
                log_event(root, mapping[row["classification"]], task=row["task_id"],
                          agent=row["agent"], pane=row["pane"], workspace=row["workspace"],
                          branch=row["branch"], reason=row.get("why"),
                          details={"classification": row["classification"],
                                   "seconds_since_activity": row["seconds_since_activity"]})
            elif row["classification"] in ("healthy", "working", "done", "idle"):
                log_event(root, {"healthy": "worker_working", "working": "worker_working",
                                 "done": "worker_idle", "idle": "worker_idle"}[row["classification"]],
                          task=row["task_id"], agent=row["agent"], pane=row["pane"],
                          branch=row["branch"],
                          details={"classification": row["classification"]})
    return report


def render(report: dict) -> str:
    lines = []
    herdr = report["herdr"]
    lines.append(f"WATCHDOG  verdict={report['verdict']}  run={report.get('run_id') or '-'}")
    if not herdr["available"]:
        lines.append(f"  herdr: UNAVAILABLE ({herdr['error']}) — filesystem signals only")
    lines.append(f"  {'task':<20} {'agent':<16} {'state':<9} {'class':<16} since_activity")
    lines.append("  " + "-" * 76)
    for row in report["tasks"]:
        since = "-" if row["seconds_since_activity"] is None else f"{row['seconds_since_activity']}s"
        lines.append(f"  {row['task_id'][:20]:<20} {(row['agent'] or '-')[:16]:<16} "
                     f"{(row['agent_state'] or '-')[:9]:<9} {row['classification']:<16} {since}")
    if report["needs_attention"]:
        lines.append("")
        lines.append("needs attention (orchestrator decides, watchdog does not):")
        for row in report["tasks"]:
            if row["task_id"] in report["needs_attention"]:
                lines.append(f"  - {row['task_id']}: {row['classification']} — {row.get('why')}")
    lines.append("")
    lines.append(f"  {report['advisory']}")
    return "\n".join(lines)


def main() -> int:
    p = argparse.ArgumentParser(description="Deterministic watchdog for orchestrated runs")
    p.add_argument("--repo-root", default=".", help="repository root holding .orchestrator/")
    p.add_argument("--json", action="store_true")
    p.add_argument("--no-herdr", action="store_true", help="filesystem signals only")
    p.add_argument("--fixture", help="JSON runtime snapshot instead of a live Herdr (tests)")
    p.add_argument("--stall-after", type=int, help="seconds without activity before 'stalled'")
    p.add_argument("--spin-after", type=int,
                   help="seconds of activity without any file change before 'spinning'")
    p.add_argument("--no-persist", action="store_true", help="do not write last_sample.json/events")
    p.add_argument("--watch", action="store_true", help="sample repeatedly (mechanical, no reasoning)")
    p.add_argument("--interval", type=int, default=60, help="seconds between samples (min 5)")
    p.add_argument("--iterations", type=int, default=0, help="0 = until interrupted")
    a = p.parse_args()

    thresholds = {}
    if a.stall_after is not None:
        thresholds["stall_after"] = a.stall_after
    if getattr(a, "spin_after", None) is not None:
        thresholds["spin_after"] = a.spin_after
    root = Path(a.repo_root).expanduser().resolve()

    if not a.watch:
        report = sample(root, use_herdr=not a.no_herdr, fixture=a.fixture,
                        thresholds=thresholds, persist=not a.no_persist)
        print(json.dumps(report, indent=2) if a.json else render(report))
        return 0 if report["verdict"] == "healthy" else 1

    interval = max(MIN_INTERVAL, a.interval)
    count = 0
    while True:
        report = sample(root, use_herdr=not a.no_herdr, fixture=a.fixture,
                        thresholds=thresholds, persist=not a.no_persist)
        print(render(report), flush=True)
        count += 1
        if a.iterations and count >= a.iterations:
            break
        time.sleep(interval)
    return 0


if __name__ == "__main__":
    sys.exit(main())
