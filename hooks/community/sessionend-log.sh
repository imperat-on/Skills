#!/usr/bin/env bash
# sessionend-log.sh
# Evento: SessionEnd | Matcher: (sem matcher; ou clear|logout|prompt_input_exit|other)
# Registra o fim da sessão (motivo, duração aproximada, branch) e faz limpeza de
# artefatos temporários do hook. SessionEnd tem budget curto (1.5s por padrão):
# este script é deliberadamente mínimo e sem rede.
# Fontes: disler/claude-code-hooks-mastery (.claude/hooks/session_end.py),
#         karanb192/claude-code-hooks (plugin standup-autopilot, hooks SessionEnd),
#         docs oficiais (SessionEnd input.reason; timeout 1.5s / variável
#         CLAUDE_CODE_SESSIONEND_HOOKS_TIMEOUT_MS).
set -uo pipefail
INPUT="$(cat)"
command -v jq >/dev/null 2>&1 || exit 0
printf '%s' "$INPUT" | jq -e . >/dev/null 2>&1 || exit 0

LOG="${CLAUDE_HOOK_LOG_DIR:-$HOME/.claude/hook-logs}"
mkdir -p "$LOG" 2>/dev/null || true
SESSIONS="${CLAUDE_HOOK_LOG_DIR:-$HOME/.claude/hook-logs}/sessions.jsonl"

printf '%s' "$INPUT" | jq -c '{ts:now, event:"SessionEnd", session_id, cwd, reason}' \
  >>"$SESSIONS" 2>/dev/null || true

# Limpeza: contadores temporários de sessão criados por outros hooks deste pacote.
CWD="$(printf '%s' "$INPUT" | jq -r '.cwd // empty')"
SID="$(printf '%s' "$INPUT" | jq -r '.session_id // empty')"
STATE="${CLAUDE_PROJECT_DIR:-${CWD:-.}}/.claude/session-state"
[[ -n "$SID" && -f "$STATE/quality-gate-${SID}.count" ]] && rm -f "$STATE/quality-gate-${SID}.count" 2>/dev/null

exit 0
