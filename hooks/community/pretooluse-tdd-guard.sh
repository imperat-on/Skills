#!/usr/bin/env bash
# pretooluse-tdd-guard.sh
# Evento: PreToolUse | Matcher: Edit|Write|MultiEdit|Bash
# Impede que o agente ADULTERE os testes para fazê-los passar (apagar asserts,
# marcar skip, relaxar expectativas) — o "TDD guard".
# Fontes: karanb192/claude-code-hooks (plugins/protect-tests, matcher
#         "Bash|Edit|MultiEdit|Write"), skill test-driven-development (regra
#         "nunca editar teste para passar"), affaan-m/everything-claude-code
#         (protect-tests citado no awesome-claude-code-hooks).
# Saída: JSON deny (permissionDecisionReason chega ao Claude).
set -uo pipefail
INPUT="$(cat)"
command -v jq >/dev/null 2>&1 || exit 0
printf '%s' "$INPUT" | jq -e . >/dev/null 2>&1 || exit 0

TOOL="$(printf '%s' "$INPUT" | jq -r '.tool_name // empty')"
FILE="$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // empty')"
CMD="$(printf '%s' "$INPUT" | jq -r '.tool_input.command // empty')"
NEW="$(printf '%s' "$INPUT" | jq -r '.tool_input.content // .tool_input.new_string // empty')"

deny() {
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"%s"}}\n' "$1"
  exit 0
}

is_test() { printf '%s' "$1" | grep -qEi '(^|/)(tests?|__tests__|spec)/|_test\.(go|py)$|\.(test|spec)\.[jt]sx?$|(^|/)test_[^/]+\.py$'; }

# 1) Ferramentas de edição apontando para arquivos de teste.
if [[ -n "$FILE" ]] && is_test "$FILE"; then
  # Ainda permitimos CRIAR testes novos; bloqueamos só a "suavização" de asserts.
  if printf '%s' "$NEW" | grep -qEi '@pytest\.mark\.skip|@unittest\.skip|\.skip\(|xit\(|xdescribe\(|test\.todo|assert True|expect\(true\)\.toBe\(true\)|# *noqa.*test'; then
    deny "BLOCKED: tentativa de desabilitar/enfraquecer um teste ($(basename "$FILE")). Conserte a implementação, não o teste."
  fi
fi

# 2) Bash removendo ou esvaziando arquivos de teste.
if [[ -n "$CMD" ]]; then
  if printf '%s' "$CMD" | grep -qEi '(rm|mv|truncate|>)[[:space:]].*(_test\.go|\.test\.[jt]sx?|\.spec\.[jt]sx?|test_[^[:space:]]*\.py)'; then
    deny "BLOCKED: remoção/truncamento de arquivo de teste detectada."
  fi
  if printf '%s' "$CMD" | grep -qEi '(pytest|vitest|jest|go test|cargo test)[^;&|]*(--(skip|exclude|ignore)|-k[[:space:]]+not)'; then
    deny "BLOCKED: execução de testes com exclusão. Rode a suíte relevante inteira."
  fi
fi
exit 0
