#!/usr/bin/env python3
"""Validate the herdr-orchestrator skill itself: frontmatter, sections, links, scripts, CLI surface.

Run before and after any edit to this skill (see references/self-modification.md):

    python3 scripts/validate_skill.py

Exit codes: 0 all checks passed, 1 at least one check failed.
"""

from __future__ import annotations

import ast
import re
import subprocess
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
SKILL_MD = SKILL_DIR / "SKILL.md"

REQUIRED_FRONTMATTER = ["name", "description", "version", "author", "license"]
REQUIRED_SECTIONS = [
    "## When to Use",
    "## Hard rules",
    "## Bootstrap",
    "## Operating modes",
    "## Run configuration: three orthogonal axes",
    "## Control plane vs data plane",
    "## Task contracts",
    "## Result contract",
    "## Scope enforcement",
    "## Roles and agent selection",
    "## Checkpoints, resume and replacement",
    "## Watchdog and events",
    "## Merge gate",
    "## Procedure",
    "## Pitfalls",
    "## Verification",
    "## References",
]
REQUIRED_MODEL_TERMS = [
    # the three orthogonal axes (v1.1)
    "coordination_mode", "team_mode", "worker_execution_mode", "team_constraints",
    "assisted", "supervised_auto", "manual", "semi_auto", "autonomous", "interactive",
    # operational robustness (v1.2)
    "Task contracts", "write_scope", "forbidden_scope", "mutation_policy",
    "TASK_CONTRACT_INVALID", "result contract", "SCOPE: FAIL", "SCOPE: PASS",
    "scope_violation", "merge_gate", "ready: false", "checkpoint", "replacement",
    "watchdog", "stalled", "prevention", "detection",
]
ORCH_COMMANDS = [
    "init", "set-modes", "modes", "propose", "add-task", "set-task", "contract", "result",
    "verify", "validate-scope", "merge-gate", "guard", "checkpoint", "replace-worker",
    "review-package", "events", "event", "ready", "status", "reconcile", "validate", "report",
]
# Scripts that expose a CLI must answer --help with exit code 0.
CLI_SCRIPTS = ["orch.py", "scope_guard.py", "watchdog.py"]
# Secret-shaped literals are assembled so this file never contains them verbatim.
SECRET_PATTERNS = [
    "Auth" + "orization:",
    "sk-" + "live",
    "ghp" + "_",
    "AK" + "IA",
]
REF_RE = re.compile(r"`((?:references|scripts)/[A-Za-z0-9._-]+)`")
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")

failures: list[str] = []
warnings: list[str] = []


def check(ok: bool, label: str, detail: str = "") -> None:
    print(f"{'PASS' if ok else 'FAIL'}  {label}" + (f" — {detail}" if detail and not ok else ""))
    if not ok:
        failures.append(label)


def parse_frontmatter(text: str):
    if not text.startswith("---\n"):
        return None, "file does not start with a frontmatter fence"
    end = text.find("\n---", 3)
    if end == -1:
        return None, "unterminated frontmatter"
    block = text[4:end + 1]
    try:
        import yaml  # type: ignore
    except ImportError:
        data = {}
        for line in block.splitlines():
            if ":" in line and not line.startswith((" ", "\t", "-")):
                k, v = line.split(":", 1)
                data[k.strip()] = v.strip()
        return data, None
    try:
        data = yaml.safe_load(block)
    except Exception as exc:  # noqa: BLE001
        return None, f"frontmatter is not valid YAML: {exc}"
    if not isinstance(data, dict):
        return None, "frontmatter is not a mapping"
    return data, None


def main() -> int:
    text = SKILL_MD.read_text(encoding="utf-8")

    # 1. frontmatter
    fm, err = parse_frontmatter(text)
    check(fm is not None, "SKILL.md has parsable YAML frontmatter", err or "")
    if fm:
        for key in REQUIRED_FRONTMATTER:
            check(bool(fm.get(key)), f"frontmatter has {key!r}")
        check(fm.get("name") == SKILL_DIR.name,
              "frontmatter name matches the directory name",
              f"name={fm.get('name')!r} dir={SKILL_DIR.name!r}")
        version = str(fm.get("version", ""))
        check(bool(VERSION_RE.match(version)), "frontmatter version is semver", version)
        desc = str(fm.get("description", ""))
        check(len(desc) >= 30, "description is descriptive enough", f"{len(desc)} chars")
        seed = " ".join(desc.split()[:9])
        check("\n" not in desc and len(seed) <= 80,
              "description stays a single short trigger line", seed)
        meta = fm.get("metadata") or {}
        hermes_meta = (meta.get("hermes") or {}) if isinstance(meta, dict) else {}
        check(bool(hermes_meta.get("tags")), "frontmatter declares hermes tags")

    # 2. required sections
    for section in REQUIRED_SECTIONS:
        check(section in text, f"SKILL.md contains section {section!r}")

    # 3. terminology present in SKILL.md (axes + the v1.2 robustness model)
    for term in REQUIRED_MODEL_TERMS:
        check(term in text, f"SKILL.md mentions {term!r}")

    # 4. links resolve and every skill file is referenced
    linked = set(REF_RE.findall(text))
    for rel in sorted(linked):
        check((SKILL_DIR / rel).is_file(), f"referenced file exists: {rel}")
    on_disk = {f"references/{p.name}" for p in (SKILL_DIR / "references").glob("*.md")}
    on_disk |= {f"scripts/{p.name}" for p in (SKILL_DIR / "scripts").glob("*.py")}
    orphan = sorted(on_disk - linked)
    check(not orphan, "every reference/script file is linked from SKILL.md", ", ".join(orphan))

    # 5. scripts compile and behave
    for script in sorted((SKILL_DIR / "scripts").glob("*.py")):
        try:
            ast.parse(script.read_text(encoding="utf-8"))
            check(True, f"{script.name} parses")
        except SyntaxError as exc:  # pragma: no cover
            check(False, f"{script.name} parses", str(exc))
    for name in CLI_SCRIPTS:
        script = SKILL_DIR / "scripts" / name
        if not script.is_file():
            check(False, f"scripts/{name} exists")
            continue
        proc = subprocess.run([sys.executable, str(script), "--help"], capture_output=True, text=True)
        check(proc.returncode == 0, f"scripts/{name} --help exits 0", proc.stderr[:160])
    orch = SKILL_DIR / "scripts" / "orch.py"
    if orch.is_file():
        proc = subprocess.run([sys.executable, str(orch), "--help"], capture_output=True, text=True)
        check(proc.returncode == 0, "scripts/orch.py --help exits 0", proc.stderr[:120])
        for cmd in ORCH_COMMANDS:
            check(cmd in proc.stdout, f"orch.py exposes the {cmd!r} command")
    adapters = SKILL_DIR / "scripts" / "scope_guard.py"
    if adapters.is_file():
        proc = subprocess.run([sys.executable, str(adapters), "adapters"],
                              capture_output=True, text=True)
        check(proc.returncode == 0 and "opencode" in proc.stdout,
              "scope_guard.py reports its prevention adapters", proc.stderr[:160])
    test_suites = ["test_orch.py", "test_watchdog.py"]
    for name in test_suites:
        check((SKILL_DIR / "scripts" / name).is_file(), f"test suite {name} exists")

    # 6. no secret-shaped literals anywhere in the skill
    offenders = []
    for path in [SKILL_MD, *sorted((SKILL_DIR / "references").glob("*.md")),
                 *sorted((SKILL_DIR / "scripts").glob("*.py"))]:
        body = path.read_text(encoding="utf-8")
        for pat in SECRET_PATTERNS:
            if pat in body:
                offenders.append(f"{path.name}:{pat}")
    check(not offenders, "no secret-shaped literals in skill files", ", ".join(offenders))

    # 7. markdown sanity for SKILL.md and every reference
    md_files = [SKILL_MD, *sorted((SKILL_DIR / "references").glob("*.md"))]
    for path in md_files:
        body = path.read_text(encoding="utf-8")
        check(body.strip() != "", f"{path.name} is non-empty")
        fences = body.count("\n```")
        check(fences % 2 == 0, f"{path.name} has balanced code fences", f"{fences} fence markers")
        if path.name != "SKILL.md":
            check(body.lstrip().startswith("# "), f"{path.name} starts with a level-1 heading")

    print()
    for w in warnings:
        print(f"WARNING: {w}")
    if failures:
        print(f"skill validation FAILED ({len(failures)} check(s))")
        return 1
    print("skill validation PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
