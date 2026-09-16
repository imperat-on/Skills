#!/usr/bin/env bash
# pretooluse-commit-message-lint.sh
# Evento: PreToolUse | Matcher: Bash (com if: "Bash(git commit *)")
# Valida a mensagem de commit ANTES de existir: exige Conventional Commits,
# tamanho do subject e proíbe menções a IA/co-autoria automática.
# Fontes: regra "commit-message validation hook" citada em awesome-claude-code-hooks
#         e tutoriais de hooks; padrão de git-safety do karanb192/claude-code-hooks.
# Env: COMMIT_REGEX (regex do subject), COMMIT_MAX_LEN (default 72)
set -uo pipefail
INPUT="$(cat)"
command -v jq >/dev/null 2>&1 || exit 0
printf '%s' "$INPUT" | jq -e . >/dev/null 2>&1 || exit 0
[[ "$(printf '%s' "$INPUT" | jq -r '.tool_name // empty')" == "Bash" ]] || exit 0

CMD="$(printf '%s' "$INPUT" | jq -r '.tool_input.command // empty')"
printf '%s' "$CMD" | grep -qE '(^|[;&|])[[:space:]]*git[[:space:]]+commit' || exit 0

deny() {
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"%s"}}\n' "$1"
  exit 0
}

MAX="${COMMIT_MAX_LEN:-72}"
# Atenção: não use ${VAR:-...{...}...} aqui — as chaves de quantificador ({1,}) fazem
# o bash expandir até o `}` errado. Monte o default em duas etapas.
DEFAULT_REGEX='^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\([a-z0-9._/-]+\))?!?: .+$'
REGEX="${COMMIT_REGEX:-$DEFAULT_REGEX}"

# Extrai a mensagem de -m "..." / -m '...' (primeira ocorrência).
MSG="$(printf '%s' "$CMD" | grep -oE -- '-m[[:space:]]+("[^"]*"|'"'"'[^'"'"']*'"'"')' | head -1 | sed -E "s/^-m[[:space:]]+//; s/^[\"']//; s/[\"']$//")"
if [[ -z "$MSG" ]]; then
  # commit via heredoc/-F: não conseguimos validar com segurança -> deixa passar,
  # mas exige que ao menos não use --no-verify (isso é pego pelo hook de git-safety).
  exit 0
fi

SUBJECT="$(printf '%s' "$MSG" | head -1)"

if ! printf '%s' "$SUBJECT" | grep -qE "$REGEX"; then
  deny "BLOCKED: mensagem de commit fora do padrão. Use Conventional Commits: 'tipo(escopo): descrição' (feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert). Recebido: '${SUBJECT}'"
fi
if [[ "${#SUBJECT}" -gt "$MAX" ]]; then
  deny "BLOCKED: subject com ${#SUBJECT} caracteres (máx ${MAX}). Resuma a mudança."
fi
if printf '%s' "$MSG" | grep -qEi 'co-authored-by: (claude|gpt|copilot|ai)|generated with .*(claude|ai)|🤖 generated'; then
  deny "BLOCKED: remova atribuição automática de IA na mensagem de commit (política do repositório)."
fi
if printf '%s' "$SUBJECT" | grep -qE '^[A-Z]|\.$'; then
  deny "BLOCKED: subject deve começar em minúscula e não terminar em ponto (Conventional Commits)."
fi
exit 0
