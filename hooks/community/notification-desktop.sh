#!/usr/bin/env bash
# notification-desktop.sh
# Evento: Notification | Matcher: permission_prompt|idle_prompt|elicitation_dialog
# Notificação de desktop portátil. Usa TERMINALSEQUENCE (OSC 777 / OSC 9), que é a
# forma oficial e race-free documentada nos docs — hooks não têm /dev/tty.
# Fonte: Claude Code docs, seção "Emit terminal notifications" (exemplo literal
#         do hook de Notification com jq -n).
# Também dispara notificação nativa quando existir notify-send/terminal-notifier.
set -uo pipefail
INPUT="$(cat)"
command -v jq >/dev/null 2>&1 || exit 0
printf '%s' "$INPUT" | jq -e . >/dev/null 2>&1 || exit 0

TITLE="Claude Code"
BODY="$(printf '%s' "$INPUT" | jq -r '.message // "Precisa da sua atenção"')"

# 1) Caminho oficial: sequência de escape devolvida no JSON (funciona em tmux/screen).
SEQ="$(printf '\033]777;notify;%s;%s\007' "$TITLE" "$BODY")"
jq -nc --arg s "$SEQ" '{terminalSequence: $s}'

# 2) Extra opcional para desktop Linux (não afeta o JSON acima, que já foi impresso).
if command -v notify-send >/dev/null 2>&1; then
  notify-send -a "$TITLE" "$BODY" >/dev/null 2>&1 &
fi
exit 0
