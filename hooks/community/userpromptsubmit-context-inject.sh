#!/usr/bin/env bash
# userpromptsubmit-context-inject.sh
# Evento: UserPromptSubmit | Matcher: (sem matcher)
# Injeta contexto a cada prompt (branch, diff resumido, hora) e registra o prompt
# em log de sessão. Também pode BLOQUEAR prompts que contenham segredos reais.
# Fontes: disler/claude-code-hooks-mastery (.claude/hooks/user_prompt_submit.py),
#         dwarvesf/claude-guardrails (full/scan-secrets.sh, UserPromptSubmit + exit 2),
#         docs oficiais (UserPromptSubmit decision control).
# Saída: JSON com additionalContext; ou {"decision":"block",...} se achar segredo.
set -uo pipefail
INPUT="$(cat)"
command -v jq >/dev/null 2>&1 || exit 0
printf '%s' "$INPUT" | jq -e . >/dev/null 2>&1 || exit 0

PROMPT="$(printf '%s' "$INPUT" | jq -r '.prompt // empty')"
CWD="$(printf '%s' "$INPUT" | jq -r '.cwd // empty')"
SESSION="$(printf '%s' "$INPUT" | jq -r '.session_id // "unknown"')"
LOG="${CLAUDE_HOOK_LOG_DIR:-$HOME/.claude/hook-logs}"
mkdir -p "$LOG" 2>/dev/null || true

# 1) Log local de prompts (JSONL) — habilita auditoria e cost tracking depois.
printf '%s' "$INPUT" | jq -c '{ts:now,session_id,prompt_len:(.prompt|length)}' >>"$LOG/user_prompts.jsonl" 2>/dev/null || true

# 2) Bloqueia segredos reais no próprio prompt (evita exfiltração via modelo).
#    Padrões clássicos, não exaustivos; combinados com o scan de segredos.
if printf '%s' "$PROMPT" | grep -qE \
  'AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----|ghp_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{22,}|sk-[A-Za-z0-9]{20,}|xox[baprs]-[A-Za-z0-9-]{10,}|AIza[0-9A-Za-z_-]{35}|eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}'; then
  jq -nc '{decision:"block",reason:"O prompt parece conter uma credencial (chave privada, token de API ou JWT). Remova o segredo e use variáveis de ambiente; se for falso positivo, reescreva o valor.",suppressOriginalPrompt:true}'
  exit 0
fi

# 3) Contexto dinâmico (fatos, não ordens).
BRANCH="$(cd "${CWD:-.}" 2>/dev/null && git rev-parse --abbrev-ref HEAD 2>/dev/null || echo '-')"
MODS="$(cd "${CWD:-.}" 2>/dev/null && git status --porcelain 2>/dev/null | wc -l | tr -d ' ')"
CTX="Ambiente: branch=${BRANCH}; arquivos modificados no working tree=${MODS}; hora=$(date -Is)."
command -v jq >/dev/null 2>&1 && jq -nc --arg c "$CTX" --arg s "sessão:$BRANCH" \
  '{hookSpecificOutput:{hookEventName:"UserPromptSubmit",additionalContext:$c,sessionTitle:$s}}'
exit 0
