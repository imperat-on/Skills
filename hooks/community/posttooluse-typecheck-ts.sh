#!/usr/bin/env bash
# posttooluse-typecheck-ts.sh
# Evento: PostToolUse | Matcher: Edit|Write|MultiEdit
# Roda `tsc --noEmit` depois de editar .ts/.tsx e devolve os erros ao Claude (exit 2).
# Fontes: padrão "tsc automático" recorrente em tutoriais de hooks (500k.io, skiln,
#         morphed/claudedirectory) e no validator ty_validator.py do disler.
# Fail-open se tsc não estiver instalado no projeto.
set -uo pipefail
INPUT="$(cat)"
command -v jq >/dev/null 2>&1 || exit 0
printf '%s' "$INPUT" | jq -e . >/dev/null 2>&1 || exit 0

FILE="$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // empty')"
case "$FILE" in *.ts|*.tsx) ;; *) exit 0 ;; esac
[[ -n "${CLAUDE_PROJECT_DIR:-}" && -d "${CLAUDE_PROJECT_DIR}/node_modules" ]] || exit 0
TSC="${CLAUDE_PROJECT_DIR}/node_modules/.bin/tsc"
[[ -x "$TSC" ]] || exit 0

OUT="$(cd "$CLAUDE_PROJECT_DIR" && "$TSC" --noEmit --pretty false 2>&1 | head -30 || true)"
[[ -z "$OUT" ]] && exit 0

echo "TypeScript: erros de tipo após editar $FILE:" >&2
printf '%s\n' "$OUT" >&2
exit 2
