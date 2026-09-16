#!/usr/bin/env bash
# stop-quality-gate.sh
# Evento: Stop | Matcher: (sem matcher)
# Gate de qualidade: antes de deixar o agente encerrar o turno, roda a suíte de
# testes/checagens do projeto. Falhou -> decision:"block" com reason; o Claude
# recebe o motivo como próxima instrução e continua trabalhando.
# Proteções: honra stop_hook_active e CAP_HITS para não criar loop infinito
# (o próprio Claude Code desiste após 8 bloqueios consecutivos).
# Fontes: docs oficiais (Stop decision control, checklist "run the test suite before
#         finishing"), prompt-hook equivalente nos docs (type:"prompt"), TDD guard
#         citado em vários tutoriais de hooks.
set -uo pipefail
INPUT="$(cat)"
command -v jq >/dev/null 2>&1 || exit 0
printf '%s' "$INPUT" | jq -e . >/dev/null 2>&1 || exit 0

# Já estamos dentro de uma continuação provocada por Stop hook? Não bloquear de novo.
[[ "$(printf '%s' "$INPUT" | jq -r '.stop_hook_active // false')" == "true" ]] && exit 0

CWD="$(printf '%s' "$INPUT" | jq -r '.cwd // empty')"
PROJ="${CLAUDE_PROJECT_DIR:-${CWD:-.}}"
cd "$PROJ" 2>/dev/null || exit 0

# Detecta o comando de teste do projeto (só roda o que está declarado).
CMD=""
if [[ -f package.json ]] && jq -e '.scripts.test' package.json >/dev/null 2>&1; then
  CMD="npm test --silent"
elif [[ -f pyproject.toml || -f pytest.ini || -d tests ]]; then
  command -v pytest >/dev/null 2>&1 && CMD="pytest -q"
elif [[ -f Cargo.toml ]]; then
  CMD="cargo test --quiet"
elif [[ -f go.mod ]]; then
  CMD="go test ./..."
fi
[[ -n "$CMD" ]] || exit 0

# Evita loops longos: no máximo 3 execuções por sessão.
STATE_DIR="$PROJ/.claude/session-state"; mkdir -p "$STATE_DIR" 2>/dev/null || true
SESSION="$(printf '%s' "$INPUT" | jq -r '.session_id // "x"')"
COUNTER="$STATE_DIR/quality-gate-${SESSION}.count"
N="$(cat "$COUNTER" 2>/dev/null || echo 0)"
[[ "$N" -ge 3 ]] && exit 0
echo $((N + 1)) >"$COUNTER" 2>/dev/null || true

OUT="$(timeout 300 bash -c "$CMD" 2>&1 | tail -30 || true)"
printf '%s' "$OUT" | grep -qiE 'fail|error|✗|FAILED|panicked' || exit 0

jq -nc --arg r "A suíte de testes do projeto falhou. Corrija antes de encerrar o turno:
$OUT" '{decision:"block", reason:$r}'
exit 0
