#!/usr/bin/env bash
# subagentstop-report-validator.sh
# Evento: SubagentStop | Matcher: "" (ou nome do agente, ex. "reviewer")
# Valida o relatório final do subagente contra um contrato mínimo (seções exigidas)
# e, se faltar, devolve decision:"block" + reason — o subagente CONTINUA rodando e
# recebe o motivo como próxima instrução.
# Fontes: docs oficiais (SubagentStop input: last_assistant_message, agent_type;
#         SubagentStop decision control), disler (.claude/hooks/subagent_stop.py).
# Env: SUBAGENT_REQUIRED_SECTIONS="Resumo;;Riscos;;Testes" (separador ;;)
set -uo pipefail
INPUT="$(cat)"
command -v jq >/dev/null 2>&1 || exit 0
printf '%s' "$INPUT" | jq -e . >/dev/null 2>&1 || exit 0

REQUIRED="${SUBAGENT_REQUIRED_SECTIONS:-Resumo;;Riscos}"
MSG="$(printf '%s' "$INPUT" | jq -r '.last_assistant_message // empty')"
AGENT="$(printf '%s' "$INPUT" | jq -r '.agent_type // "subagente"')"

MISSING=""
IFS=';;' read -r -a SECTIONS <<<"$REQUIRED"
for s in "${SECTIONS[@]}"; do
  [[ -z "$s" ]] && continue
  printf '%s' "$MSG" | grep -qiE "(^|[^a-z])${s}([^a-z]|$)" || MISSING+="- ${s}"$'\n'
done

# Contrato mínimo adicional: tamanho e ausência de placeholders.
[[ "${#MSG}" -lt 200 ]] && MISSING+="- relatório com menos de 200 caracteres"$'\n'
printf '%s' "$MSG" | grep -qE 'TODO|TBD|<preencher>|lorem ipsum' && MISSING+="- contém placeholders (TODO/TBD)"$'\n'

[[ -z "$MISSING" ]] && exit 0

jq -nc --arg r "O relatório de '$AGENT' não atende ao contrato. Faltando:
${MISSING}Complemente o relatório e só então encerre." \
  '{decision:"block", reason:$r}'
exit 0
