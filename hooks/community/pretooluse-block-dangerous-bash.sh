#!/usr/bin/env bash
# pretooluse-block-dangerous-bash.sh
# Evento: PreToolUse | Matcher: Bash (ou Bash|PowerShell)
# Bloqueia comandos destrutivos de shell antes de executarem.
# Fontes: dwarvesf/claude-guardrails (full/settings.json), disler/claude-code-hooks-mastery
#         (.claude/hooks/pre_tool_use.py), karanb192/claude-code-hooks (block-dangerous-commands).
# Saída: JSON hookSpecificOutput.permissionDecision=deny (Claude vê o motivo).
# Alternativa equivalente: echo msg >&2; exit 2
# Requer: jq. Sem jq, falha-aberto (exit 0) para nunca travar a sessão.
set -uo pipefail

INPUT="$(cat)"

command -v jq >/dev/null 2>&1 || exit 0
printf '%s' "$INPUT" | jq -e . >/dev/null 2>&1 || exit 0

TOOL="$(printf '%s' "$INPUT" | jq -r '.tool_name // empty')"
[[ "$TOOL" == "Bash" || "$TOOL" == "PowerShell" ]] || exit 0
CMD="$(printf '%s' "$INPUT" | jq -r '.tool_input.command // empty')"
[[ -n "$CMD" ]] || exit 0

deny() {
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"%s"}}\n' "$1"
  exit 0
}

# 1) rm -rf apontando para raiz/home/glob perigoso
if printf '%s' "$CMD" | grep -qEi '(^|[;&|[:space:]])rm[[:space:]]+.*-[a-zA-Z]*(r[a-zA-Z]*f|f[a-zA-Z]*r)[[:space:]]+([/~*.]|\.\.|\$HOME)'; then
  deny "BLOCKED: rm -rf em caminho crítico (/, ~, *, ..). Use trash-cli ou mova para /tmp antes."
fi
# rm -rf sem path explícito (ex.: rm -rf . )
if printf '%s' "$CMD" | grep -qEi '(^|[;&|[:space:]])rm[[:space:]]+.*-[a-zA-Z]*(r[a-zA-Z]*f|f[a-zA-Z]*r)[[:space:]]*(\.|\./)?[[:space:]]*($|[;&|])'; then
  deny "BLOCKED: rm -rf sem alvo explícito. Seja específico sobre o caminho."
fi
# 2) destruição de disco / sobrescrita de device
if printf '%s' "$CMD" | grep -qEi '(^|[;&|[:space:]])(mkfs(\.[a-z0-9]+)?|dd[[:space:]]+.*of=/dev/|shred[[:space:]]+/dev/)'; then
  deny "BLOCKED: comando de formatação/escrita em device detectado."
fi
# 3) fork bomb
if printf '%s' "$CMD" | grep -qF ':(){ :|:& };:'; then
  deny "BLOCKED: fork bomb."
fi
# 4) pipe-to-shell (executar script remoto sem inspeção)
if printf '%s' "$CMD" | grep -qEi '(curl|wget)[^|]*\|[[:space:]]*(sudo[[:space:]]+)?(ba|z|)sh'; then
  deny "BLOCKED: pipe-to-shell. Baixe o script, inspecione e só então execute."
fi
# 5) escalada de permissão silenciosa dentro da sessão
if printf '%s' "$CMD" | grep -qEi -- '--dangerously-skip-permissions|--bypass-permissions|--dangerously-bypass-approvals'; then
  deny "BLOCKED: escalada de permissões não é permitida de dentro da sessão."
fi
# 6) chown/chmod recursivo em raiz ou home
if printf '%s' "$CMD" | grep -qEi 'chmod[[:space:]]+.*-R[[:space:]]+777[[:space:]]+(/|~|\$HOME)$|chown[[:space:]]+.*-R[[:space:]]+.*[[:space:]]+(/|~|\$HOME)$'; then
  deny "BLOCKED: chmod/chown recursivo em raiz/home."
fi
# 7) exfiltração para serviços de colheita de dados
if printf '%s' "$CMD" | grep -qEi '(curl|wget|nc|ncat)[^|]*(webhook\.site|requestbin|pipedream|hookbin|interact\.sh|canarytokens|ngrok\.io)'; then
  deny "BLOCKED: possível exfiltração de dados para serviço externo."
fi

exit 0
