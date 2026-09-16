#!/usr/bin/env bash
# pretooluse-git-safety.sh
# Evento: PreToolUse | Matcher: Bash
# Impede: push direto em main/master/production, force-push, commit --no-verify,
#         reset --hard destrutivo e reescrita de histórico em branch compartilhada.
# Fontes: dwarvesf/claude-guardrails (push protegido), karanb192/claude-code-hooks
#         (plugins/git-safety), regra anti --no-verify documentada por Anthropic.
# Saída: JSON deny. Fail-open.
set -uo pipefail
INPUT="$(cat)"
command -v jq >/dev/null 2>&1 || exit 0
printf '%s' "$INPUT" | jq -e . >/dev/null 2>&1 || exit 0
[[ "$(printf '%s' "$INPUT" | jq -r '.tool_name // empty')" == "Bash" ]] || exit 0
CMD="$(printf '%s' "$INPUT" | jq -r '.tool_input.command // empty')"
[[ -n "$CMD" ]] || exit 0

deny() {
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"%s"}}\n' "$1"
  exit 0
}

# push direto para branch protegida (considera prefixos de comando e && / ; / |)
if printf '%s' "$CMD" | grep -qEi '(^|[&|;(])[[:space:]]*git[[:space:]]+push([[:space:]]|$)[^;&|]*\b(main|master|production|prod)\b'; then
  deny "BLOCKED: push direto em main/master/production. Crie uma feature branch e abra PR."
fi
# force push / push --mirror / push :branch
if printf '%s' "$CMD" | grep -qEi 'git[[:space:]]+push[[:space:]]+.*(--force([[:space:]]|$)|-f([[:space:]]|$)|--mirror|--delete)'; then
  deny "BLOCKED: force-push reescreve histórico compartilhado. Use --force-with-lease em branch de feature."
fi
# pular hooks de pre-commit
if printf '%s' "$CMD" | grep -qEi 'git[[:space:]]+commit[^;&|]*--no-verify|git[[:space:]]+commit[^;&|]*[[:space:]]-n([[:space:]]|$)'; then
  deny "BLOCKED: --no-verify pula pre-commit/pre-push. Corrija a causa da falha."
fi
# reescrita de histórico
if printf '%s' "$CMD" | grep -qEi 'git[[:space:]]+(filter-branch|filter-repo)|git[[:space:]]+rebase[[:space:]]+.*--root|git[[:space:]]+update-ref[[:space:]]+-d'; then
  deny "BLOCKED: reescrita de histórico exige confirmação humana explícita."
fi
# descarte irreversível de trabalho
if printf '%s' "$CMD" | grep -qEi 'git[[:space:]]+(reset[[:space:]]+--hard|clean[[:space:]]+-[a-z]*f[a-z]*d|checkout[[:space:]]+--[[:space:]]+\.)'; then
  deny "BLOCKED: descarte de alterações não commitadas. Faça commit/stash antes."
fi
# commits em nome de outro autor / bypass de assinatura
if printf '%s' "$CMD" | grep -qEi 'git[[:space:]]+commit[^;&|]*--(author|committer)=' ; then
  deny "BLOCKED: falsificar autoria de commit."
fi
exit 0
