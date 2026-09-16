#!/usr/bin/env bash
# postcompact-reminder.sh
# Evento: PostCompact | Matcher: manual|auto
# Depois da compactação, reinjeta as regras do projeto e o índice do snapshot
# pré-compactação — cura a "amnésia pós-compactação".
# Fonte: Dicklesworthstone/post_compact_reminder (github.com/Dicklesworthstone/
#        post_compact_reminder, ~54 stars) — hook que detecta compactação e manda
#        re-ler AGENTS.md; adaptado para emitir additionalContext no PostCompact.
# PostCompact não tem decision control: saída é apenas informativa/efeito colateral.
set -uo pipefail
INPUT="$(cat)"
command -v jq >/dev/null 2>&1 || exit 0
printf '%s' "$INPUT" | jq -e . >/dev/null 2>&1 || exit 0

CWD="$(printf '%s' "$INPUT" | jq -r '.cwd // empty')"
PROJ="${CLAUDE_PROJECT_DIR:-${CWD:-.}}"
STATE="$PROJ/.claude/session-state"
SNAP="$(cat "$STATE/latest" 2>/dev/null || echo '(nenhum)')"

FILES=""
for f in AGENTS.md CLAUDE.md .claude/rules/*.md; do
  [[ -f "$PROJ/$f" ]] && FILES+=$(printf '\n- %s' "$f")
done

CTX="A compactação de contexto acabou de ocorrer. Arquivos de regras do projeto que
devem ser relidos antes de continuar:${FILES:-
- (nenhum encontrado)}
Snapshot do estado anterior: ${SNAP}"

if command -v jq >/dev/null 2>&1; then
  jq -nc --arg c "$CTX" '{hookSpecificOutput:{hookEventName:"PostCompact",additionalContext:$c}}'
else
  printf '%s\n' "$CTX"
fi
exit 0
