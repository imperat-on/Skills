#!/usr/bin/env python3
"""scope-guard — o worker escreve só dentro do escopo do contrato.

Evento:  pre_tool_call (Hermes) / PreToolUse (Claude Code, Cursor)
Contrato: exit 2 = bloqueia, motivo no stderr. exit 0 = deixa passar.

Como funciona: o orquestrador (`herdr-orchestrator`, `guard --plan --kind hermes`) grava
`<worktree>/.orchestrator-contract.json` com o `write_scope`/`forbidden_scope` da tarefa.
Este hook procura esse arquivo subindo a partir do diretório de trabalho da chamada. Se ele
NÃO existir, a sessão não é de um worker e o hook não interfere em nada.

Duas portas, porque uma só não basta (medido no opencode: um worker com `edit` negado
simplesmente escreveu pelo shell):
  - a ferramenta de arquivo (`write_file`, `patch`): pelo `file_path`
  - o shell (`terminal`): por redirecionamento (`>`, `>>`), `tee`, `sed -i`, `cp`/`mv` destino

Fora do escopo, o alvo é classificado com a MESMA implementação do orquestrador
(`skills/orchestration/herdr-orchestrator/scripts/scope_guard.py`). Se essa importação falhar,
o hook NÃO bloqueia (fail-open) e avisa no stderr: sem a fonte única de verdade, bloquear com
uma cópia divergente quebraria trabalho legítimo. O `commit gate` e a validação de escopo
pós-hoc continuam valendo como rede.
"""
import json
import os
import re
import sys
from pathlib import Path

CONTRACT_NAME = ".orchestrator-contract.json"
PATH_FIELDS = ("file_path", "path", "file", "filename", "target", "destination")
ALWAYS_OK_PREFIXES = ("/dev/", "$", "%")
SHELL_WRITE_PATTERNS = (
    re.compile(r"(?:>>?)\s*([^\s;&|><]+)"),                      # > arq   >> arq
    re.compile(r"\btee(?:\s+-a)?\s+([^\s;&|><]+)"),              # tee arq
    re.compile(r"\bsed\s+-i[^\s]*\s+(?:-e\s+\S+\s+)?([^\s;&|><]+)"),  # sed -i s/x/y/ arq
    re.compile(r"\b(?:cp|mv|install|ln)\s+(?:-\S+\s+)*\S+\s+([^\s;&|><]+)"),  # cp a b -> b
)


def load_tool() -> tuple[str, dict, dict]:
    """(tool_name, tool_input, payload). `extra.tool_input` é o formato do dispatcher do Hermes
    quando um payload sintético é mesclado (`hermes hooks test --payload-file`)."""
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return "", {}, {}
    if not isinstance(payload, dict):
        return "", {}, {}
    ti = payload.get("tool_input")
    if not isinstance(ti, dict):
        ti = {}
    extra = payload.get("extra")
    if isinstance(extra, dict) and isinstance(extra.get("tool_input"), dict):
        merged = dict(extra["tool_input"])
        merged.update(ti)
        ti = merged
    return str(payload.get("tool_name", "")), ti, payload


def first(ti: dict, *keys: str) -> str:
    for k in keys:
        v = ti.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""


def block(reason: str) -> None:
    sys.stderr.write(
        f"BLOQUEADO pelo scope-guard: {reason}\n"
        "O worker só escreve dentro do write_scope do contrato. Amplie o contrato no "
        "orquestrador se isto for trabalho legítimo.\n"
    )
    sys.exit(2)


def find_contract(start) -> tuple[Path | None, dict]:
    p = Path(str(start)).expanduser()
    try:
        p = p.resolve()
    except OSError:
        return None, {}
    for cand in [p, *p.parents]:
        f = cand / CONTRACT_NAME
        if f.is_file():
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                return f, {}
            return f, data if isinstance(data, dict) else {}
    return None, {}


def load_matcher():
    """A mesma classificação do orquestrador (fonte única de verdade)."""
    here = Path(__file__).resolve()
    for base in (here.parents[2] if len(here.parents) > 2 else here.parent,):
        cand = base / "skills" / "orchestration" / "herdr-orchestrator" / "scripts"
        if (cand / "scope_guard.py").is_file():
            sys.path.insert(0, str(cand))
            try:
                import scope_guard  # noqa: PLC0415
                return scope_guard
            except Exception as exc:  # pragma: no cover
                sys.stderr.write(f"scope-guard: nao consegui importar o scope_guard: {exc}\n")
                return None
    return None


def shell_targets(command: str) -> list[str]:
    out = []
    for rx in SHELL_WRITE_PATTERNS:
        for m in rx.finditer(command):
            t = m.group(1).strip().strip("'\"")
            if t and not t.startswith(ALWAYS_OK_PREFIXES) and t not in ("&1", "&2"):
                out.append(t)
    return out


def targets(tool: str, ti: dict) -> list[str]:
    out = []
    for key in PATH_FIELDS:
        v = ti.get(key)
        if isinstance(v, str) and v.strip():
            out.append(v.strip())
    command = first(ti, "command", "cmd", "script", "shell_command")
    if command:
        out.extend(shell_targets(command))
    return out


def classify_target(target: str, contract: dict, worktree: Path, sg) -> str | None:
    """Motivo do bloqueio, ou None se o alvo passa."""
    raw = target
    p = Path(raw).expanduser()
    if not p.is_absolute():
        p = (worktree / p)
    try:
        p = p.resolve()
    except OSError:
        return None
    wt = worktree.resolve() if worktree else None
    try:
        rel = p.relative_to(wt) if wt else None
    except ValueError:
        rel = None
    if rel is None:
        return (f"escrita fora do worktree: {raw} -> {p} (o worker só escreve dentro de "
                f"{wt})")
    verdict = sg.classify_paths([str(rel)], contract)
    if verdict.get("violations"):
        v = verdict["violations"][0]
        return f"{rel} viola o escopo ({v.get('kind')}): {v.get('reason') or ''}".strip()
    return None


def main() -> int:
    tool, ti, payload = load_tool()
    cwd = (first(ti, "cwd", "workdir") or (payload.get("cwd") if isinstance(payload.get("cwd"), str)
                                           else "") or os.getcwd())
    contract_file, contract = find_contract(cwd)
    if not contract:
        return 0                                   # sessão normal: não é worker de run
    worktree = Path(str(contract.get("worktree") or Path(str(contract_file)).parent))
    sg = load_matcher()
    if sg is None:
        sys.stderr.write(
            "scope-guard: contrato encontrado mas o matcher do orquestrador nao esta acessivel; "
            "NAO bloqueando (fail-open). Ajuste o caminho do kit ou reinstale os hooks.\n")
        return 0
    for target in targets(tool, ti):
        reason = classify_target(target, contract, worktree, sg)
        if reason:
            block(f"tarefa {contract.get('task_id')}: {reason}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
