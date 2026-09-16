#!/usr/bin/env bash
# stop-notify-telegram.sh
# Evento: Stop | Matcher: (sem matcher)
# Envia mensagem no Telegram ao fim do turno, com projeto, branch e resumo.
# Credenciais APENAS por env var: TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID.
# Fonte: gist g761007 "Claude Code Stop hook — Telegram bot notification with
#        project, summary, ctx%, model and rate limit"; hqtrung/claude-notification-hook.
# Nunca bloqueia: exit 0 sempre.
set -uo pipefail
INPUT="$(cat)"
command -v jq >/dev/null 2>&1 || exit 0
printf '%s' "$INPUT" | jq -e . >/dev/null 2>&1 || exit 0

: "${TELEGRAM_BOT_TOKEN:?defina TELEGRAM_BOT_TOKEN}"
: "${TELEGRAM_CHAT_ID:?defina TELEGRAM_CHAT_ID}"

CWD="$(printf '%s' "$INPUT" | jq -r '.cwd // ""')"
PROJ="$(basename "${CWD:-?}")"
BRANCH="$(cd "${CWD:-.}" 2>/dev/null && git rev-parse --abbrev-ref HEAD 2>/dev/null || echo '-')"
SUMMARY="$(printf '%s' "$INPUT" | jq -r '.last_assistant_message // "(sem resumo)"' | tr -s ' \n' ' ' | head -c 600)"
TOKENS="$(printf '%s' "$INPUT" | jq -r '[.background_tasks[]?] | length' 2>/dev/null || echo 0)"

TEXT=$'\xf0\x9f\xa4\x96 *Claude Code* — turno conclu\xc3\xaddo\n'
TEXT+="projeto: \`${PROJ}\` | branch: \`${BRANCH}\` | tarefas em voo: ${TOKENS}"$'\n\n'
TEXT+="${SUMMARY}"

curl -sS --max-time 10 \
  "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
  -d "chat_id=${TELEGRAM_CHAT_ID}" \
  --data-urlencode "text=${TEXT}" \
  -d "parse_mode=Markdown" \
  -d "disable_web_page_preview=true" >/dev/null 2>&1 || true

exit 0
