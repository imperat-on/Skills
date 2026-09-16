#!/usr/bin/env bash
# notify-stop.sh — avisa quando o agente termina de responder.
#
# Evento:  Stop (Claude Code) / post_llm_call (Hermes)
# Contrato: exit 0 sempre; nunca atrapalha o fim do turno.
#
# Canais, na ordem: desktop (notify-send / osascript) e, se NTFY_URL ou
# SKILLS_KIT_WEBHOOK estiver definido, um POST via curl. Nada é obrigatório.
set -u

payload=$(cat)
[ -z "${payload// /}" ] && exit 0

# pausa curta para o turno terminar de renderizar antes do toast
sleep "${SKILLS_KIT_NOTIFY_DELAY:-1}"

msg=$(printf '%s' "$payload" | python3 -c '
import json, sys, os
try:
    d = json.load(sys.stdin)
except Exception:
    d = {}
for k in ("last_assistant_message", "message", "response", "summary"):
    v = d.get(k)
    if isinstance(v, str) and v.strip():
        v = " ".join(v.split())
        print(v[:160]); raise SystemExit
print("turno concluído em " + (d.get("cwd") or os.getcwd()).rstrip("/").split("/")[-1])
' 2>/dev/null)
[ -z "${msg:-}" ] && msg="turno concluído"

title="${SKILLS_KIT_NOTIFY_TITLE:-agente de código}"

if command -v notify-send >/dev/null 2>&1; then
  notify-send -a "$title" -u low "✔ pronto" "$msg" >/dev/null 2>&1 || true
elif command -v osascript >/dev/null 2>&1; then
  osascript -e "display notification \"${msg//\"/}\" with title \"$title\"" >/dev/null 2>&1 || true
elif command -v terminal-notifier >/dev/null 2>&1; then
  terminal-notifier -title "$title" -message "$msg" >/dev/null 2>&1 || true
fi

endpoint="${NTFY_URL:-${SKILLS_KIT_WEBHOOK:-}}"
if [ -n "$endpoint" ] && command -v curl >/dev/null 2>&1; then
  printf '%s' "$msg" | curl -sS -m 5 -X POST --data-binary @- "$endpoint" >/dev/null 2>&1 || true
fi

exit 0
