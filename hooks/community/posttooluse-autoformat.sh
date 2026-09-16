#!/usr/bin/env bash
# posttooluse-autoformat.sh
# Evento: PostToolUse | Matcher: Edit|Write|MultiEdit
# Roda o formatador correto por extensão no arquivo que o agente acabou de editar.
# Fontes: karanb192/claude-code-hooks (plugins/format-code), 500k.io/skiln/blakecrosley
#         tutoriais de auto-format (prettier/ruff/black), disler (validators ruff/ty).
# Saída: silencioso (exit 0). Para FORÇAR o modelo a corrigir, use
#        posttooluse-lint-guard.sh (exit 2). Fail-open: formatador ausente não bloqueia.
set -uo pipefail
INPUT="$(cat)"
command -v jq >/dev/null 2>&1 || exit 0
printf '%s' "$INPUT" | jq -e . >/dev/null 2>&1 || exit 0

FILE="$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // empty')"
[[ -n "$FILE" && -f "$FILE" ]] || exit 0
LOG="${CLAUDE_HOOK_LOG:-/tmp/claude-hooks-autofmt.log}"

run() {  # executa só se o binário existir; nunca deixa erro vazar para o transcript
  command -v "$1" >/dev/null 2>&1 || return 0
  shift
  "$@" >/dev/null 2>>"$LOG" || echo "$(date -Is) format falhou: $*" >>"$LOG"
}

case "$FILE" in
  *.js|*.jsx|*.ts|*.tsx|*.json|*.css|*.scss|*.md|*.html|*.yaml|*.yml)
      if   [[ -f "$(dirname "$FILE")/../../.prettierrc"* ]] || command -v prettier >/dev/null 2>&1; then run prettier npx --no-install prettier --write "$FILE"
      fi ;;
  *.py)
      if   command -v ruff >/dev/null 2>&1; then run ruff ruff format "$FILE"; run ruff ruff check --fix --quiet "$FILE"
      elif command -v black >/dev/null 2>&1; then run black black -q "$FILE"
      fi ;;
  *.go)  run gofmt gofmt -w "$FILE" ;;
  *.rs)  run rustfmt rustfmt "$FILE" ;;
  *.sh|*.bash) run shfmt shfmt -w "$FILE" ;;
  *.lua) run stylua stylua "$FILE" ;;
  *.rb)  run rubocop rubocop -A --fail-level E "$FILE" ;;
  *.php) run php-cs-fixer php-cs-fixer fix "$FILE" ;;
  *.kt)  run ktlint ktlint -F "$FILE" ;;
  *.java) run google-java-format google-java-format -i "$FILE" ;;
  *.tf)  run terraform terraform fmt "$FILE" ;;
esac
exit 0
