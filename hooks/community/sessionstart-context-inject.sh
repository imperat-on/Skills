#!/usr/bin/env bash
# sessionstart-context-inject.sh
# Evento: SessionStart | Matcher: startup|resume|clear|fork
# Injeta contexto dinâmico no início da sessão: branch, últimos commits,
# arquivos modificados, TODOs e comandos do projeto.
# Fontes: disler/claude-code-hooks-mastery (.claude/hooks/session_start.py,
#         get_git_status), obra/superpowers (session-start), docs oficiais
#         (SessionStart decision control -> additionalContext / sessionTitle).
# Saída: JSON com hookSpecificOutput.additionalContext.
set -uo pipefail
INPUT="$(cat)"
CWD="$(printf '%s' "${INPUT:-{}}" | jq -r '.cwd // empty' 2>/dev/null || true)"
[[ -n "$CWD" ]] || CWD="$(pwd)"
cd "$CWD" 2>/dev/null || exit 0

BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo '-')"
COMMITS="$(git log --oneline -5 2>/dev/null | sed 's/^/  /' || true)"
CHANGES="$(git status --porcelain 2>/dev/null | head -15 || true)"
TESTS=""
[[ -f package.json ]] && TESTS="$(jq -r '.scripts.test // empty' package.json 2>/dev/null || true)"
[[ -z "$TESTS" && -f pyproject.toml ]] && TESTS="pytest"
[[ -z "$TESTS" && -f Cargo.toml ]] && TESTS="cargo test"
[[ -z "$TESTS" && -f go.mod ]] && TESTS="go test ./..."

CTX="Estado do repositório em $(date -Is)
branch atual: ${BRANCH}
últimos commits:
${COMMITS:-  (nenhum)}
alterações não commitadas:
${CHANGES:-  (limpo)}"
[[ -n "$TESTS" ]] && CTX+=$'\ncomando de teste do projeto: '"$TESTS"

# Escreve texto como FATOS (não como ordens) para não disparar as defesas de prompt-injection.
if command -v jq >/dev/null 2>&1; then
  jq -nc --arg c "$CTX" --arg t "claude:${BRANCH}" \
    '{hookSpecificOutput:{hookEventName:"SessionStart",additionalContext:$c,sessionTitle:$t}}'
else
  printf '%s\n' "$CTX"   # stdout puro também vira contexto em SessionStart
fi
exit 0
