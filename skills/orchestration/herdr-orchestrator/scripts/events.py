#!/usr/bin/env python3
"""Append-only operational event log (.orchestrator/events.jsonl). stdlib only.

Shared by scripts/orch.py (orchestrator) and scripts/watchdog.py (deterministic observer) so both
processes write one consistent, crash-safe log. Every append takes an exclusive lock and is
redacted: secret-shaped keys are dropped before anything touches the disk.

Event vocabulary is fixed and documented (references/watchdog-and-events.md). Unknown event names
are still accepted by `log_event` (the watchdog and future stages must not be blocked by a missing
constant), but `orch.py event` warns about them unless `--allow-unknown` is passed.
"""

from __future__ import annotations

import fcntl
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

EVENT_KINDS = [
    # run / planning
    "run_initialised", "mode_changed", "run_paused", "run_cancelled", "run_finished",
    "task_created", "task_updated", "contract_written", "contract_invalid", "task_direct_override",
    # workers
    "worker_spawned", "worker_started", "worker_working", "worker_idle", "worker_blocked",
    "worker_stalled", "worker_failed", "worker_replaced", "worker_output_observed",
    "launch_verified", "result_collected",
    # checkpoints
    "checkpoint_created",
    # scope
    "scope_checked", "scope_violation", "scope_guard_installed", "scope_guard_verified",
    "scope_guard_unavailable",
    # checks / tests
    "test_started", "test_passed", "test_failed",
    # review
    "review_started", "review_passed", "review_failed", "fix_cycle_started", "fix_cycle_closed",
    # recovery / watchdog
    "recovery_started", "recovery_reconciled", "watchdog_sample", "watchdog_alert",
    "watchdog_degraded",
    # integration / cleanup
    "integration_started", "integration_passed", "integration_failed", "merge_gate_evaluated",
    "merge_gate_bypassed", "merged", "cleanup_started", "cleanup_finished",
    # misc
    "verify_run", "skill_proposal_recorded",
]

SECRET_KEY_RE = re.compile(
    r"(token|secret|passw|api[_-]?key|apikey|authorization|auth_?header|cookie|credential)", re.I)
# Secret-shaped values are assembled so this module never contains them verbatim.
SECRET_VALUE_RES = [
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}"),
    re.compile(r"\b" + "ghp" + "_[A-Za-z0-9]{20,}"),
    re.compile(r"\b" + "AK" + "IA[0-9A-Z]{12,}"),
    re.compile(r"\bBearer\s+[A-Za-z0-9._-]{20,}", re.I),
]

DEFAULT_PATH = Path(".orchestrator") / "events.jsonl"


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def events_path(root: Path) -> Path:
    return Path(root) / DEFAULT_PATH


def _redact(data: dict) -> tuple[dict, list]:
    """Drop secret-shaped keys/values. Returns (clean mapping, dropped key names)."""
    clean, dropped = {}, []
    for key, value in data.items():
        if SECRET_KEY_RE.search(str(key)):
            dropped.append(str(key))
            continue
        if isinstance(value, str):
            redacted = value
            for pat in SECRET_VALUE_RES:
                redacted = pat.sub("***", redacted)
            if redacted != value:
                dropped.append(f"{key}(value)")
            value = redacted
        clean[key] = value
    return clean, dropped


def run_id_of(root: Path) -> str | None:
    """Best-effort run id from state.json; never raises (the log must keep working)."""
    try:
        state = json.loads((Path(root) / ".orchestrator" / "state.json").read_text(encoding="utf-8"))
        return state.get("run_id")
    except (OSError, ValueError):
        return None


def log_event(root: Path, event: str, task=None, **data) -> dict:
    """Append one JSON object. Crash-safe (flock + single write) and secret-free."""
    path = events_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    rec = {"time": now()}
    run_id = data.pop("run_id", None) or run_id_of(root)
    if run_id:
        rec["run_id"] = run_id
    rec["event"] = event
    if task:
        rec["task"] = task
        rec["task_id"] = task
    clean, dropped = _redact({k: v for k, v in data.items() if v is not None})
    rec.update(clean)
    if dropped:
        rec["redacted"] = sorted(set(dropped))
    line = json.dumps(rec, sort_keys=False) + "\n"
    with open(path, "a", encoding="utf-8") as fh:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        try:
            fh.write(line)
            fh.flush()
            os.fsync(fh.fileno())
        finally:
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
    return rec


def read_events(root: Path, limit: int | None = None) -> list:
    """Parse events.jsonl, skipping (never failing on) malformed lines."""
    path = events_path(root)
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    return out[-limit:] if limit else out


def last_event_for(events: list, task: str, kinds=None) -> dict | None:
    for rec in reversed(events):
        if rec.get("task") == task or rec.get("task_id") == task:
            if kinds is None or rec.get("event") in kinds:
                return rec
    return None
