#!/usr/bin/env bash
# stop-notify-ntfy.sh
# Evento: Stop | Matcher: (sem matcher)
# Envia push via ntfy.sh quando o agente termina o turno. Sem segredo hardcoded:
# o tópico vem de NTFY_TOPIC (e opcionalmente NTFY_SERVER / NTFY_TOKEN).
# Fontes: pacote claude-code-ntfy-notification-hook (PyPI), padrão "notify on Stop"
#         do disler/claude-code-hooks-mastery (.claude/hooks/stop.py), HN "6 hooks".
# Não bloqueia o Stop: sempre exit 0.
set -uo pipefail
INPUT="$(cat)"
command -v jq >/dev/null 2>&1 || exit 0
printf '%s' "$INPUT" | jq -e . >/dev/null 2>&1 || exit 0

: "${NTFY_TOPIC:?defina NTFY_TOPIC no ambiente (settings.json env ou shell)}"
SERVER="${NTFY_SERVER:-https://ntfy.sh}"

MSG="$(printf '%s' "$INPUT" | jq -r '.last_assistant_message // "Turno concluído"' | head -c 400)"
CWD="$(printf '%s' "$INPUT" | jq -r '.cwd // ""')"
BRANCH="$(cd "$CWD" 2>/dev/null && git rev-parse --abbrev-ref HEAD 2>/dev/null || echo '-')"

# Prioridade: NTFY_TOKEN é opcional (tópico protegido por Bearer).
AUTH=()
[[ -n "${NTFY_TOKEN:-}" ]] && AUTH=(-H "Authorization: Bearer ${NTFY_TOKEN}")

curl -sS --max-time 10 "${AUTH[@]}" \
  -H "Title: Claude Code — turno concluído" \
  -H "Tags: robot,bell" \
  -H "Priority: default" \
  -d "[${BRANCH}] ${MSG}" \
  "${SERVER}/${NTFY_TOPIC}" >/dev/null 2>&1 || true

exit 0
