#!/usr/bin/env bash
# audit-log.sh — registra toda chamada de ferramenta em JSONL.
#
# Evento:  post_tool_call (Hermes) / PostToolUse (Claude Code, Cursor)
# Contrato: exit 0 sempre; escreve uma linha JSON em
#   ${XDG_STATE_HOME:-$HOME/.local/state}/skills-kit/audit.jsonl
#
# Serve para reconstruir o que o agente fez numa sessão (post-mortem, custo,
# "por que esse arquivo mudou?"). Segredos óbvios são redigidos antes de
# gravar: o log não é lugar para chave de API.
set -u

payload=$(cat)
[ -z "${payload// /}" ] && exit 0

LOG_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/skills-kit"
mkdir -p "$LOG_DIR" 2>/dev/null || exit 0

SKILLS_KIT_PAYLOAD="$payload" LOG_FILE="$LOG_DIR/audit.jsonl" python3 - <<'PY' 2>/dev/null || exit 0
import json, os, re, time

log = os.environ["LOG_FILE"]
try:
    d = json.loads(os.environ.get("SKILLS_KIT_PAYLOAD", "{}"))
except Exception:
    raise SystemExit(0)

ti = d.get("tool_input") if isinstance(d.get("tool_input"), dict) else {}
SECRET = re.compile(
    r"(sk-[A-Za-z0-9_-]{12,}|ghp_[A-Za-z0-9]{20,}|gho_[A-Za-z0-9]{20,}|"
    r"AKIA[0-9A-Z]{12,}|AIza[0-9A-Za-z_-]{20,}|xox[baprs]-[A-Za-z0-9-]{10,}|"
    r"bearer\s+[A-Za-z0-9._-]{16,}|(token|secret|password|passwd|api[_-]?key)"
    r"[\"'=:\s]+[A-Za-z0-9._\-/+]{12,})",
    re.IGNORECASE,
)

def redact(v):
    if isinstance(v, str):
        return SECRET.sub("***", v)
    if isinstance(v, dict):
        return {k: redact(x) for k, x in v.items()}
    if isinstance(v, list):
        return [redact(x) for x in v]
    return v

target = ""
for k in ("command", "file_path", "path", "pattern", "url", "query", "prompt"):
    v = ti.get(k)
    if isinstance(v, str) and v:
        target = v
        break

entry = {
    "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    "event": d.get("hook_event_name") or "post_tool_call",
    "tool": d.get("tool_name"),
    "target": redact(target)[:500],
    "input_keys": sorted(ti.keys()),
    "cwd": d.get("cwd"),
    "session": d.get("session_id"),
}
with open(log, "a", encoding="utf-8") as fh:
    fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
PY

exit 0
