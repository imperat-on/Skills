#!/usr/bin/env bash
# posttooluse-lint-guard.sh
# Evento: PostToolUse | Matcher: Edit|Write|MultiEdit
# Roda o linter no arquivo editado e, se houver erro NOVO, devolve stderr + exit 2
# para o Claude ver e corrigir na mesma volta (em PostToolUse, exit 2 não desfaz a
# escrita — apenas mostra o stderr ao modelo).
# Fontes: disler/claude-code-hooks-mastery (.claude/hooks/validators/ruff_validator.py,
#         ty_validator.py), affaan-m "auto-lint on save", 500k.io tutorial.
# Requer: jq (fail-open sem ele).
set -uo pipefail
INPUT="$(cat)"
command -v jq >/dev/null 2>&1 || exit 0
printf '%s' "$INPUT" | jq -e . >/dev/null 2>&1 || exit 0

FILE="$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // empty')"
[[ -n "$FILE" && -f "$FILE" ]] || exit 0
OUT=""

case "$FILE" in
  *.py)
      if command -v ruff >/dev/null 2>&1; then
        OUT="$(ruff check --quiet --output-format=concise "$FILE" 2>&1 || true)"
      elif command -v flake8 >/dev/null 2>&1; then
        OUT="$(flake8 "$FILE" 2>&1 || true)"
      fi ;;
  *.js|*.jsx|*.ts|*.tsx)
      if command -v npx >/dev/null 2>&1 && npx --no-install eslint --version >/dev/null 2>&1; then
        OUT="$(npx --no-install eslint --no-color "$FILE" 2>&1 || true)"
      fi ;;
  *.go) OUT="$(command -v golangci-lint >/dev/null 2>&1 && golangci-lint run "$FILE" 2>&1 || true)" ;;
  *.sh) OUT="$(command -v shellcheck >/dev/null 2>&1 && shellcheck -S warning "$FILE" 2>&1 || true)" ;;
  *.rs) OUT="$(command -v cargo >/dev/null 2>&1 && cargo clippy --quiet --message-format short 2>&1 | head -20 || true)" ;;
  *) exit 0 ;;
esac

# Ignora avisos triviais que o linter às vezes emite com o binário ausente
case "$OUT" in
  ""|*"not found"*|*"command not found"*) exit 0 ;;
esac

echo "Lint falhou em $FILE — corrija antes de seguir:" >&2
printf '%s\n' "$OUT" | head -40 >&2
exit 2   # visível ao Claude; a escrita já ocorreu (PostToolUse não desfaz)
