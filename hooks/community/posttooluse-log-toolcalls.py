#!/usr/bin/env python3
"""posttooluse-log-toolcalls.py

Evento: PostToolUse | Matcher: "" (todos) ou "Edit|Write|Bash"
Log estruturado de cada chamada de ferramenta (JSONL), base para observabilidade,
auditoria e cost tracking. Equivalente ao `event-logger.py` do karanb192/claude-code-hooks
(plugins/session-logger) e ao logger do disler/claude-code-hooks-mastery.

Fonte : disler/claude-code-hooks-mastery (.claude/hooks/post_tool_use.py),
        karanb192/claude-code-hooks (utils/event-logger.py, plugin session-logger).
Saída : nenhuma (exit 0). Nunca bloqueia.
Env   : CLAUDE_HOOK_LOG_DIR (default ~/.claude/hook-logs)
"""
import json
import os
import sys
import time
from pathlib import Path

MAX_FIELD = 2000


def trunc(v):
    s = json.dumps(v, ensure_ascii=False, default=str)
    return s if len(s) <= MAX_FIELD else s[:MAX_FIELD] + "...[truncated]"


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0

    log_dir = Path(os.environ.get("CLAUDE_HOOK_LOG_DIR", Path.home() / ".claude" / "hook-logs"))
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        return 0

    tool_input = data.get("tool_input") or {}
    # Redação: nunca gravar conteúdo potencialmente sensível de campos de arquivo.
    redacted_keys = {"content", "new_string", "old_string", "password", "token", "api_key"}
    safe_input = {
        k: ("[redacted]" if k in redacted_keys else v) for k, v in tool_input.items()
    }

    record = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "session_id": data.get("session_id"),
        "prompt_id": data.get("prompt_id"),
        "hook_event": data.get("hook_event_name"),
        "tool_name": data.get("tool_name"),
        "tool_use_id": data.get("tool_use_id"),
        "duration_ms": data.get("duration_ms"),
        "cwd": data.get("cwd"),
        "agent_type": data.get("agent_type"),
        "permission_mode": data.get("permission_mode"),
        "tool_input": trunc(safe_input),
    }

    day = time.strftime("%Y-%m-%d")
    with open(log_dir / ("tool-calls-%s.jsonl" % day), "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
