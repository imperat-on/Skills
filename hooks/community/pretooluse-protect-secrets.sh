#!/usr/bin/env bash
# pretooluse-protect-secrets.sh
# Evento: PreToolUse | Matcher: Read|Edit|Write|MultiEdit|Bash
# Impede ler/editar/despejar arquivos de segredo (.env, chaves, credenciais, wallet).
# Fontes: disler/claude-code-hooks-mastery (.claude/hooks/pre_tool_use.py is_env_file_access),
#         karanb192/claude-code-hooks (plugins/protect-secrets),
#         dwarvesf/claude-guardrails (permissions.deny + scan-secrets).
# Saída: JSON deny. Fail-open se jq ausente.
set -uo pipefail
INPUT="$(cat)"
command -v jq >/dev/null 2>&1 || exit 0
printf '%s' "$INPUT" | jq -e . >/dev/null 2>&1 || exit 0

TOOL="$(printf '%s' "$INPUT" | jq -r '.tool_name // empty')"
FILE="$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // empty')"
CMD="$(printf '%s' "$INPUT" | jq -r '.tool_input.command // empty')"

deny() {
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"%s"}}\n' "$1"
  exit 0
}

# Templates/exemplos são permitidos: nunca bloqueie .env.example et al.
is_template() { printf '%s' "$1" | grep -qEi '\.env\.(example|sample|template|schema|defaults)$|example\.env$|\.example$'; }

# --- 1) ferramentas de arquivo (Read/Edit/Write/MultiEdit) ---
if [[ -n "$FILE" ]]; then
  NORM="${FILE//\\//}"   # Windows: normaliza separadores antes de comparar
  if ! is_template "$NORM"; then
    case "$NORM" in
      */.env|*.env|*/\.env.*|*.env.*)   deny "BLOCKED: .env contém segredos. Use .env.example e variáveis de ambiente." ;;
      */.envrc)                          deny "BLOCKED: .envrc (direnv) pode conter segredos." ;;
      */.ssh/*|*/id_rsa|*/id_ed25519|*/id_ecdsa) deny "BLOCKED: chave SSH privada." ;;
      */.aws/credentials|*/.aws/config)  deny "BLOCKED: credenciais AWS." ;;
      */.gnupg/*|*/.kube/config|*/.docker/config.json|*/.netrc|*/.npmrc|*/.pypirc|*/.git-credentials) deny "BLOCKED: arquivo de credenciais do usuário." ;;
      *.pem|*.p12|*.pfx|*.keystore)      deny "BLOCKED: material criptográfico (certificado/chave)." ;;
      */secrets/*|*/credentials/*)       deny "BLOCKED: diretório de segredos." ;;
    esac
    # padrão sem âncora: qualquer nome contendo secret/credential (exceto templates)
    printf '%s' "$NORM" | grep -qEi '/(secrets?|credentials?)\.(json|ya?ml|toml|ini)$' && \
      deny "BLOCKED: arquivo de segredos por convenção de nome."
  fi
fi

# --- 2) Bash: leitura/despejo/envio de segredos ---
if [[ -n "$CMD" ]]; then
  is_template "$CMD" && exit 0
  printf '%s' "$CMD" | grep -qEi '(cat|bat|less|more|head|tail|grep|cp|mv|scp|rsync|echo|printf|source|\.)[[:space:]].*\.env([^.]|$)' && \
    deny "BLOCKED: acesso a .env via shell. Use variáveis de ambiente exportadas."
  printf '%s' "$CMD" | grep -qEi '(^|[;&|[:space:]])(printenv|env)([[:space:]]|$)' && \
    deny "BLOCKED: dump de variáveis de ambiente pode expor segredos."
  printf '%s' "$CMD" | grep -qEi 'cat[[:space:]]+(~|\$HOME)?/?\.(ssh|aws|gnupg|kube)/' && \
    deny "BLOCKED: leitura de diretório de credenciais."
  # Exfiltração: segredo enviado para host remoto
  printf '%s' "$CMD" | grep -qEi '(curl|wget|nc|ncat|http)[^|]*\.(env|pem|key)([^a-z0-9]|$)' && \
    deny "BLOCKED: possível exfiltração de arquivo de segredo."
fi

exit 0
