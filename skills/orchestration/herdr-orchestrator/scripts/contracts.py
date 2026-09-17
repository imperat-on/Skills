#!/usr/bin/env python3
"""Task, result and checkpoint contracts + the deterministic merge gate. stdlib only.

Pure logic: no git, no network, no filesystem mutation. `orch.py`, `scope_guard.py` and
`watchdog.py` all import from here, so there is exactly one definition of what a contract is and
exactly one definition of when a branch may be integrated.

Design rules:
- a contract is data, never prose: it is validated *before* delegation and re-used by the scope
  validator, the reviewer, the fix loop and recovery;
- a worker's result report is communication, never evidence: `result` is parsed and stored, but the
  merge gate only trusts fields the orchestrator verified itself (scope, worktree, commit, tests,
  review);
- every gate decision prints its reasons, so nothing depends on the orchestrator's mood.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone

CONTRACT_VERSION = 1
CHECKPOINT_VERSION = 1

RESULT_STATES = ["DONE", "BLOCKED", "FAILED", "NEEDS_INPUT"]
TASK_ROLES = ["worker", "researcher", "tester", "reviewer", "fixer"]
MUTATION_POLICIES = ["worktree_only", "read_only", "temp_dirs_only", "branch_only"]
CHECKPOINT_POLICIES = ["auto", "required", "none"]
VERDICTS = ["PASS", "FAIL"]

FIELD_ORDER = [
    "task_id", "role", "objective", "depends_on", "write_scope", "read_scope", "forbidden_scope",
    "acceptance_criteria", "required_checks", "deliverables", "branch", "worktree", "base_commit",
    "worker", "agent_kind", "model", "budget_tokens", "budget_usd", "mutation_policy",
    "when_blocked", "scope_justification",
    "checkpoint_policy", "phase_plan", "notes",
]
LIST_FIELDS = ["depends_on", "write_scope", "read_scope", "forbidden_scope", "acceptance_criteria",
               "required_checks", "deliverables", "phase_plan", "notes"]

# Fields a mutating task cannot be delegated without (a read-only task only needs the first three).
REQUIRED_MUTATING = ["task_id", "role", "objective", "write_scope", "acceptance_criteria",
                     "base_commit", "mutation_policy"]
REQUIRED_READONLY = ["task_id", "role", "objective"]

DEFAULT_WHEN_BLOCKED = ("report the blocked reason to the orchestrator; do not expand scope, do not "
                        "switch task, do not answer trust/credential prompts")
DEFAULT_BY_ROLE = {
    "worker": "worktree_only",
    "fixer": "worktree_only",
    "reviewer": "read_only",
    "researcher": "read_only",
    "tester": "temp_dirs_only",
}

# Role policies (references/task-contracts.md): what a role may do, and the write zoning it gets.
ROLE_POLICIES = {
    "orchestrator": {
        "may": ["plan", "read metadata", "inspect git", "inspect diffs", "run and verify commands",
                "coordinate", "integrate approved work", "persist state", "manage herdr"],
        "may_not": ["implement delegated work silently", "take over a delegated task"],
        "write_zone": "state and run-owned resources only",
    },
    "worker": {
        "may": ["read what the task needs", "write inside write_scope", "run the required checks",
                "create its own focused commit on its branch"],
        "may_not": ["expand its own scope", "touch files outside the contract",
                    "start another task on its own", "merge its branch",
                    "touch another worker's worktree/branch/pane"],
        "write_zone": "write_scope inside its own worktree",
    },
    "reviewer": {
        "may": ["read code", "read the diff", "run non-mutating checks", "produce a VERDICT"],
        "may_not": ["edit code", "commit", "change the implementation"],
        "write_zone": "read-only (scratch output only)",
    },
    "tester": {
        "may": ["run test plans", "reproduce and diagnose failures", "write only into authorized "
                "temp/build/cache directories"],
        "may_not": ["change the implementation", "commit product code"],
        "write_zone": "temp/build/cache directories only",
    },
    "fixer": {
        "may": ["change the original task branch inside the original scope",
                "address the findings it was sent"],
        "may_not": ["refactor beyond the findings", "touch other tasks' branches"],
        "write_zone": "original task branch + scope",
    },
    "researcher": {
        "may": ["read", "report structured findings"],
        "may_not": ["edit project files"],
        "write_zone": "read-only",
    },
}


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


# --------------------------------------------------------------------------- YAML/JSON loading

def parse_simple_yaml(text: str):
    """Small deterministic YAML subset: nested mappings, `- item` lists, list-of-mappings,
    inline `[]` / `{}`, quoted scalars, comments.

    Deliberately not a full YAML implementation: contracts are written in this subset, and callers
    fall back to PyYAML when it happens to be installed.
    """
    lines = []
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#") or stripped in ("---", "..."):
            continue
        indent = len(raw) - len(raw.lstrip(" \t"))
        lines.append((indent, stripped))
    if not lines:
        return {}
    value, _ = _parse_block(lines, 0, lines[0][0])
    return value


def _strip_comment(s: str) -> str:
    out, quote = [], None
    for i, ch in enumerate(s):
        if quote:
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
        elif ch == "#" and (i == 0 or s[i - 1] in " \t"):
            break
        out.append(ch)
    return "".join(out).strip()


def _split_kv(text: str):
    if ":" not in text:
        return text.strip(), None
    key, value = text.split(":", 1)
    return key.strip(), _strip_comment(value).strip()


def _scalar(value):
    if value is None:
        return None
    v = value.strip()
    if v in ("", "~", "null"):
        return None
    if v.startswith("[") and v.endswith("]"):
        inner = v[1:-1].strip()
        if not inner:
            return []
        return [_scalar(p) for p in _split_inline(inner)]
    if v.startswith("{") and v.endswith("}"):
        inner = v[1:-1].strip()
        out = {}
        if inner:
            for part in _split_inline(inner):
                k, val = part.split(":", 1) if ":" in part else (part, "")
                out[k.strip().strip("\"'")] = _scalar(val)
        return out
    if v in ("true", "True", "yes"):
        return True
    if v in ("false", "False", "no"):
        return False
    if re.fullmatch(r"-?\d+", v):
        return int(v)
    return v.strip("\"'")


def _split_inline(inner: str) -> list:
    parts, buf, quote = [], [], None
    for ch in inner:
        if quote:
            if ch == quote:
                quote = None
            buf.append(ch)
            continue
        if ch in "\"'":
            quote = ch
            buf.append(ch)
            continue
        if ch == ",":
            parts.append("".join(buf).strip())
            buf = []
            continue
        buf.append(ch)
    if buf:
        parts.append("".join(buf).strip())
    return [p for p in parts if p != ""]


def _parse_block(lines, i: int, indent: int):
    if i >= len(lines):
        return {}, i
    if lines[i][1].startswith("- ") or lines[i][1] == "-":
        return _parse_list(lines, i, indent)
    return _parse_map(lines, i, indent)


def _parse_list(lines, i: int, indent: int):
    out = []
    while i < len(lines) and lines[i][0] == indent and (lines[i][1].startswith("- ")
                                                        or lines[i][1] == "-"):
        item = lines[i][1][1:].strip()
        i += 1
        if item.startswith("{"):
            out.append(_scalar(item))
            continue
        key, value = _split_kv(item)
        if value is not None or (":" in item and not item.startswith(("\"", "'"))):
            entry = {key: _scalar(value)}
            while i < len(lines) and lines[i][0] > indent and not lines[i][1].startswith("- "):
                k2, v2 = _split_kv(lines[i][1])
                i += 1
                if v2 is None and i < len(lines) and lines[i][0] > indent:
                    sub, i = _parse_block(lines, i, lines[i][0])
                    entry[k2] = sub
                else:
                    entry[k2] = _scalar(v2)
            out.append(entry)
        else:
            out.append(_scalar(item))
    return out, i


def _parse_map(lines, i: int, indent: int):
    out = {}
    while i < len(lines) and lines[i][0] == indent and not lines[i][1].startswith("- "):
        key, value = _split_kv(lines[i][1])
        i += 1
        if value is None or value == "":
            if i < len(lines) and lines[i][0] > indent:
                sub, i = _parse_block(lines, i, lines[i][0])
                out[key] = sub
            elif value is None:
                out[key] = None
            else:
                out[key] = ""
        else:
            out[key] = _scalar(value)
    return out, i


def load_structured_text(text: str):
    """JSON first (canonical), then PyYAML if importable, then the built-in subset parser."""
    stripped = text.strip()
    if not stripped:
        return {}
    if stripped[0] in "[{":
        return json.loads(stripped)
    try:
        import yaml  # type: ignore
        data = yaml.safe_load(stripped)
        if isinstance(data, (dict, list)):
            return data
    except Exception:  # noqa: BLE001 - optional dependency, fall through to the subset parser
        pass
    return parse_simple_yaml(stripped)


# --------------------------------------------------------------------------- task contract

def normalize_contract(raw: dict, task_id: str | None = None) -> dict:
    c = dict(raw or {})
    if task_id:
        c.setdefault("task_id", task_id)
    for field in LIST_FIELDS:
        if field in c and c[field] is None:
            c[field] = []
        elif isinstance(c.get(field), str):
            c[field] = [x.strip() for x in c[field].split(",") if x.strip()]
    c.setdefault("depends_on", [])
    c.setdefault("write_scope", [])
    c.setdefault("read_scope", ["**"])
    c.setdefault("forbidden_scope", [])
    c.setdefault("acceptance_criteria", [])
    c.setdefault("required_checks", [])
    c.setdefault("deliverables", [])
    c.setdefault("notes", [])
    c.setdefault("when_blocked", DEFAULT_WHEN_BLOCKED)
    c.setdefault("checkpoint_policy", "auto")
    role = c.get("role")
    if not c.get("mutation_policy") and role in DEFAULT_BY_ROLE:
        c["mutation_policy"] = DEFAULT_BY_ROLE[role]
    c["contract_version"] = CONTRACT_VERSION
    if c.get("objective") is not None and not isinstance(c["objective"], str):
        c["objective"] = " ".join(str(x) for x in c["objective"])
    return c


def is_mutating(contract: dict) -> bool:
    """A contract mutates the project tree when its policy allows writes there.

    `read_only` never mutates; `temp_dirs_only` (tester) is confined to scratch/build dirs and does
    not count as a project mutation; an empty write_scope does NOT make a worker read-only - it makes
    the contract invalid, because a writer with no declared scope is exactly what v1.2 forbids.
    """
    policy = contract.get("mutation_policy")
    return policy in ("worktree_only", "branch_only")


def write_scope_is_broad(contract: dict) -> bool:
    scope = [str(p).strip() for p in contract.get("write_scope") or []]
    return any(p in ("**", "*", "/**", "./**", "**/*") for p in scope)


def validate_contract(raw: dict) -> dict:
    """Structural validation, run BEFORE delegation. Returns {errors, warnings, mutating, ...}."""
    c = normalize_contract(raw)
    errors, warnings = [], []
    mutating = is_mutating(c)
    required = REQUIRED_MUTATING if mutating else REQUIRED_READONLY

    if c.get("role") not in TASK_ROLES:
        errors.append(f"role must be one of {TASK_ROLES} (got {c.get('role')!r})")
    for field in required:
        value = c.get(field)
        if value in (None, "", [], {}):
            errors.append(f"missing required field {field!r} for a "
                          f"{'mutating' if mutating else 'read-only'} task")
    if c.get("objective") and len(str(c["objective"])) < 10:
        warnings.append("objective looks too short to be actionable")
    if mutating:
        if write_scope_is_broad(c) and not c.get("scope_justification"):
            errors.append("write_scope is a catch-all pattern — set scope_justification (and expect "
                          "an escalation) or narrow the scope")
        if not c.get("forbidden_scope"):
            warnings.append("no forbidden_scope declared: the contract does not name the zones the "
                            "worker must stay out of")
        if not c.get("required_checks"):
            warnings.append("no required_checks declared: nothing forces the worker to run its own "
                            "checks before reporting")
        policy = c.get("mutation_policy")
        if policy not in MUTATION_POLICIES:
            errors.append(f"mutation_policy must be one of {MUTATION_POLICIES} (got {policy!r})")
        if not c.get("worktree"):
            warnings.append("no worktree recorded in the contract yet (set it before dispatch)")
    if not c.get("acceptance_criteria") and mutating:
        errors.append("no acceptance_criteria: the task is unverifiable and the reviewer has "
                      "nothing to judge")
    if c.get("checkpoint_policy") not in CHECKPOINT_POLICIES:
        errors.append(f"checkpoint_policy must be one of {CHECKPOINT_POLICIES}")
    if c.get("phase_plan") and c.get("checkpoint_policy") == "none":
        warnings.append("phase_plan declared but checkpoint_policy is 'none'")
    return {
        "task_id": c.get("task_id"),
        "mutating": mutating,
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
    }


def render_contract(raw: dict) -> str:
    """Render the contract as YAML for the worker prompt / reviewer prompt / reports."""
    c = normalize_contract(raw)
    lines = []
    for field in FIELD_ORDER:
        if field not in c:
            continue
        value = c[field]
        if isinstance(value, list):
            if not value:
                lines.append(f"{field}: []")
                continue
            lines.append(f"{field}:")
            for item in value:
                lines.append(f"  - {item}")
        elif isinstance(value, dict):
            lines.append(f"{field}:")
            for k, v in value.items():
                lines.append(f"  {k}: {v}")
        elif value is None:
            lines.append(f"{field}: null")
        else:
            lines.append(f"{field}: {value}")
    return "\n".join(lines)


# --------------------------------------------------------------------------- result contract

RESULT_FIELD_ORDER = ["result", "task_id", "commit", "changed_files", "tests", "scope_violations",
                      "blockers", "notes"]


def parse_result(text: str) -> dict:
    """Parse a worker result report. Accepts JSON or the key/value + list shape from prompts.md."""
    if not text or not text.strip():
        return {"result": None, "parse_error": "empty result report"}
    try:
        data = load_structured_text(text)
    except ValueError as exc:
        return {"result": None, "parse_error": f"unparsable result report: {exc}"}
    if not isinstance(data, dict):
        return {"result": None, "parse_error": "result report is not a mapping"}
    if "result" not in data:
        for key in ("status", "STATUS"):
            if key in data:
                data["result"] = data.pop(key)
                break
    out = dict(data)
    if isinstance(out.get("result"), str):
        out["result"] = out["result"].strip().upper()
    for field in ("changed_files", "scope_violations", "blockers", "notes", "tests"):
        val = out.get(field)
        if val is None:
            out[field] = []
        elif isinstance(val, str):
            out[field] = [x.strip() for x in val.split(",") if x.strip()]
    if isinstance(out.get("tests"), (str, dict)):
        out["tests"] = [out["tests"]] if isinstance(out["tests"], dict) else []
    return out


def validate_result(res: dict) -> dict:
    errors, warnings = [], []
    state = res.get("result")
    if state not in RESULT_STATES:
        errors.append(f"result must be one of {RESULT_STATES} (got {state!r})")
    if state == "DONE":
        for field in ("commit", "changed_files"):
            if not res.get(field):
                errors.append(f"result DONE requires {field!r}")
    if state == "BLOCKED" and not res.get("blockers"):
        errors.append("result BLOCKED requires at least one blocker entry")
    for test in res.get("tests") or []:
        if not isinstance(test, dict):
            warnings.append(f"test entry is not a mapping ({test!r}) — command/exit_code expected")
            continue
        if test.get("exit_code") is None:
            warnings.append(f"test entry without exit_code ({test.get('command')!r}): an unverified "
                            f"test claim")
    return {"valid": not errors, "errors": errors, "warnings": warnings}


# --------------------------------------------------------------------------- checkpoints

def normalize_checkpoint(raw: dict, task_id: str | None = None) -> dict:
    cp = dict(raw or {})
    if task_id:
        cp.setdefault("task_id", task_id)
    for field in ("completed", "current", "remaining", "changed_files", "decisions", "blockers"):
        val = cp.get(field)
        if val is None:
            cp[field] = []
        elif isinstance(val, str):
            cp[field] = [x.strip() for x in val.split(",") if x.strip()]
    cp.setdefault("phase", 0)
    cp.setdefault("total_phases", 0)
    cp.setdefault("last_known_commit", None)
    cp.setdefault("worker", None)
    cp["checkpoint_version"] = CHECKPOINT_VERSION
    cp.setdefault("created_at", now())
    return cp


def validate_checkpoint(cp: dict) -> dict:
    errors, warnings = [], []
    if not cp.get("task_id"):
        errors.append("checkpoint without task_id")
    if not isinstance(cp.get("phase"), int):
        errors.append("phase must be an integer")
    if not isinstance(cp.get("total_phases"), int):
        errors.append("total_phases must be an integer")
    if cp.get("remaining") == [] and not cp.get("completed"):
        warnings.append("checkpoint has neither completed nor remaining work — it carries no state")
    if cp.get("phase") and cp.get("total_phases") and cp["phase"] > cp["total_phases"]:
        errors.append("phase greater than total_phases")
    for field in ("completed", "current", "remaining", "decisions", "blockers"):
        if not isinstance(cp.get(field), list):
            errors.append(f"checkpoint.{field} must be a list")
    return {"valid": not errors, "errors": errors, "warnings": warnings}


def render_checkpoint(cp: dict) -> str:
    cp = normalize_checkpoint(cp)
    lines = ["checkpoint:",
             f"  task_id: {cp['task_id']}",
             f"  phase: {cp['phase']}",
             f"  total_phases: {cp['total_phases']}"]
    for field in ("completed", "current", "remaining"):
        lines.append(f"  {field}:")
        lines += [f"    - {x}" for x in (cp[field] or [])] or ["    - (none)"]
    lines.append(f"  last_known_commit: {cp.get('last_known_commit') or 'null'}")
    lines.append("  changed_files:")
    lines += [f"    - {x}" for x in (cp.get("changed_files") or [])] or ["    - (none)"]
    lines.append("  decisions:")
    lines += [f"    - {x}" for x in (cp.get("decisions") or [])] or ["    - (none)"]
    lines.append("  blockers:")
    lines += [f"    - {x}" for x in (cp.get("blockers") or [])] or ["    - none"]
    return "\n".join(lines)


def checkpoint_required(contract: dict) -> bool:
    """Decide whether a task justifies checkpoints. Never force them on small tasks."""
    policy = (contract or {}).get("checkpoint_policy", "auto")
    if policy == "required":
        return True
    if policy == "none":
        return False
    phases = (contract or {}).get("phase_plan") or []
    if len(phases) > 1:
        return True
    # auto: long/complex = several acceptance criteria, dependencies, or an explicit phase count
    return len((contract or {}).get("acceptance_criteria") or []) >= 3


# --------------------------------------------------------------------------- merge gate

GATE_KEYS = ["contract", "result", "scope", "tests", "review", "worktree", "commit", "blockers",
             "fix_cycles"]


def merge_gate(task: dict, *, verified_scope: dict | None = None, tests: dict | None = None,
               worktree_clean: bool | None = None, commit_exists: bool | None = None) -> dict:
    """Compute the merge gate. Pure: every observation is passed in by the caller.

    A branch may only be integrated when every field is `pass`/`clean`/`present`/`none`/`closed`.
    """
    contract = task.get("contract") or {}
    contract_valid = bool(contract) and validate_contract(contract)["valid"]
    mutating = bool(task.get("mutates_files")) or (bool(contract) and is_mutating(contract))
    if not contract and not mutating:
        contract_valid = True          # nothing to constrain: no scope, no branch to integrate
    result = task.get("result") or {}
    scope = verified_scope or task.get("scope_validation") or {}
    tests = tests or task.get("tests") or {}
    worktree_clean = worktree_clean if worktree_clean is not None else task.get("worktree_clean")
    commit_exists = commit_exists if commit_exists is not None else bool(task.get("commit"))
    blockers = [b for b in (result.get("blockers") or []) if str(b).strip()]
    blockers += [str(b) for b in (task.get("blockers") or []) if str(b).strip()]
    violations = (scope.get("violations") or []) if isinstance(scope, dict) else []
    verdict = (task.get("verdict") or "").upper()
    review_ok = verdict == "PASS"
    tests_status = (tests.get("status") or "").lower()

    fields = {
        "contract": "pass" if contract_valid else ("missing" if not contract else "fail"),
        "result": ("collected" if result.get("result") else "missing"),
        "scope": "pass" if scope.get("status") == "PASS" and not violations else (
            "missing" if not scope else "fail"),
        "tests": "pass" if tests_status in ("pass", "passed") else (
            "missing" if not tests_status else "fail"),
        "review": "pass" if review_ok else ("missing" if not verdict else "fail"),
        "worktree": {True: "clean", False: "dirty", None: "unknown"}[worktree_clean],
        "commit": "present" if commit_exists else "missing",
        "blockers": "none" if not blockers else f"{len(blockers)}",
        "fix_cycles": "closed" if not task.get("fix_cycles_open") else "open",
    }
    pass_values = {"contract": {"pass"}, "result": {"collected"}, "scope": {"pass"},
                   "tests": {"pass"}, "review": {"pass"}, "worktree": {"clean"},
                   "commit": {"present"}, "blockers": {"none"}, "fix_cycles": {"closed"}}
    reasons = []
    for key in GATE_KEYS:
        if fields[key] not in pass_values[key]:
            reasons.append(f"{key}={fields[key]}")
    if any(v.get("kind") == "forbidden" for v in violations if isinstance(v, dict)):
        reasons.append("unresolved forbidden_scope violation")
    return {
        "ready": not reasons,
        "fields": fields,
        "reasons": reasons,
        "scope_violations": [v for v in violations if isinstance(v, dict)],
        "blockers": blockers,
        "verdict": verdict or None,
        "evaluated_at": now(),
    }


def render_merge_gate(gate: dict) -> str:
    lines = ["merge_gate:"]
    for key in GATE_KEYS:
        lines.append(f"  {key}: {gate['fields'][key]}")
    lines.append(f"  ready: {str(bool(gate['ready'])).lower()}")
    if gate.get("reasons"):
        lines.append(f"  reasons: {', '.join(gate['reasons'])}")
    return "\n".join(lines)


def contract_digest(contract: dict) -> str:
    """Stable hash of the material contract fields: a worker may not change them unnoticed."""
    import hashlib
    material = {k: contract.get(k) for k in
                ("task_id", "role", "objective", "write_scope", "forbidden_scope",
                 "acceptance_criteria", "required_checks", "base_commit", "mutation_policy",
                 "branch", "worktree")}
    blob = json.dumps(material, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:16]


PATTERN_KEYS_RE = re.compile(r"^(write_scope|forbidden_scope|read_scope)$")


def scope_patterns(contract: dict, key: str) -> list:
    return [str(p) for p in (contract.get(key) or []) if str(p).strip()]
