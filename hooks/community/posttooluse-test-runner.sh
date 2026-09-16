#!/usr/bin/env bash
# posttooluse-test-runner.sh
# Evento: PostToolUse | Matcher: Edit|Write|MultiEdit
# Roda os testes relacionados ao arquivo editado e devolve falhas ao Claude (exit 2).
# Evita a suíte completa: deriva o alvo do caminho (pytest -k / vitest relacionado).
# Fontes: padrão "run tests after file changes" (docs oficiais, seção Run hooks in the
#         background), blakecrosley tutorial (test runner hook).
# Fail-open quando não há runner detectável. Use async:true no settings para não travar.
set -uo pipefail
INPUT="$(cat)"
command -v jq >/dev/null 2>&1 || exit 0
printf '%s' "$INPUT" | jq -e . >/dev/null 2>&1 || exit 0

FILE="$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // empty')"
[[ -n "$FILE" && -f "$FILE" ]] || exit 0
PROJ="${CLAUDE_PROJECT_DIR:-$(pwd)}"
OUT=""

# Nunca rodar testes ao editar o próprio teste? (opcional) — descomente para pular:
# case "$FILE" in *test*|*spec*) exit 0 ;; esac

case "$FILE" in
  *.py)
      if [[ -f "$PROJ/pyproject.toml" || -f "$PROJ/pytest.ini" || -d "$PROJ/tests" ]]; then
        if command -v pytest >/dev/null 2>&1; then
          MOD="$(printf '%s' "$FILE" | sed "s|^$PROJ/||; s|/|.|g; s|\.py$||")"
          OUT="$(cd "$PROJ" && timeout 120 pytest -q -x -k "$(basename "${MOD##*.}")" 2>&1 | tail -25 || true)"
        fi
      fi ;;
  *.ts|*.tsx|*.js|*.jsx)
      if [[ -f "$PROJ/package.json" ]] && command -v npx >/dev/null 2>&1; then
        if npx --no-install vitest --version >/dev/null 2>&1; then
          OUT="$(cd "$PROJ" && timeout 120 npx --no-install vitest run --silent "$FILE" 2>&1 | tail -25 || true)"
        elif npx --no-install jest --version >/dev/null 2>&1; then
          OUT="$(cd "$PROJ" && timeout 120 npx --no-install jest --silent --runTestsByPath "$FILE" 2>&1 | tail -25 || true)"
        fi
      fi ;;
  *) exit 0 ;;
esac

case "$OUT" in ""|*"no tests ran"*|*"No tests found"*) exit 0 ;; esac
printf '%s' "$OUT" | grep -qiE 'fail|error|✗|FAILED' || exit 0

echo "Testes falharam após editar $FILE:" >&2
printf '%s\n' "$OUT" >&2
exit 2
