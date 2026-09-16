#!/usr/bin/env bash
# precompact-snapshot.sh
# Evento: PreCompact | Matcher: manual|auto
# Antes da compactação: salva snapshot do transcript e extrai fatos úteis
# (branch, arquivos tocados, TODOs) em .claude/session-state/, para que o contexto
# perdido possa ser re-injetado depois (ver postcompact-reminder.sh).
# Fonte: Dicklesworthstone/post_compact_reminder (54 stars, PostCompact +
#        re-leitura de AGENTS.md), parcadei/Continuous-Claude-v3 (ledgers/handoffs),
#        docs oficiais (PreCompact input: trigger, custom_instructions).
# PreCompact PODE bloquear (exit 2) — este script nunca bloqueia: exit 0.
set -uo pipefail
INPUT="$(cat)"
command -v jq >/dev/null 2>&1 || exit 0
printf '%s' "$INPUT" | jq -e . >/dev/null 2>&1 || exit 0

TRIGGER="$(printf '%s' "$INPUT" | jq -r '.trigger // "unknown"')"
TRANSCRIPT="$(printf '%s' "$INPUT" | jq -r '.transcript_path // empty')"
CWD="$(printf '%s' "$INPUT" | jq -r '.cwd // empty')"
STATE_DIR="${CLAUDE_PROJECT_DIR:-${CWD:-.}}/.claude/session-state"
mkdir -p "$STATE_DIR" 2>/dev/null || exit 0

TS="$(date +%Y%m%d-%H%M%S)"
SNAP="$STATE_DIR/precompact-${TS}.md"

{
  echo "# Snapshot pré-compactação (${TS}, trigger=${TRIGGER})"
  echo
  echo "## Branch"
  (cd "${CWD:-.}" && git rev-parse --abbrev-ref HEAD 2>/dev/null; git log --oneline -5 2>/dev/null) || true
  echo
  echo "## Working tree"
  (cd "${CWD:-.}" && git status --porcelain 2>/dev/null | head -40) || true
  echo
  echo "## TODOs abertos no repo"
  (cd "${CWD:-.}" && grep -rn --include='*.py' --include='*.ts' --include='*.tsx' --include='*.js' \
      --include='*.go' --include='*.rs' -E 'TODO|FIXME|XXX' . 2>/dev/null | head -25) || true
  echo
  echo "## Instruções de projeto carregadas"
  for f in AGENTS.md CLAUDE.md README.md; do
    [[ -f "${CWD:-.}/$f" ]] && echo "- ${f} (re-ler após compactação)"
  done
} >"$SNAP" 2>/dev/null || true

# Mantém apenas os 20 snapshots mais recentes.
ls -1t "$STATE_DIR"/precompact-*.md 2>/dev/null | tail -n +21 | xargs -r rm -f 2>/dev/null || true

# Índice do snapshot mais recente, para o hook de PostCompact/Stop usar.
printf '%s' "$SNAP" >"$STATE_DIR/latest" 2>/dev/null || true

# Registro em log (stderr em hook de exit 0 vai só para o debug log — evite ruído).
printf '%s precompact snapshot=%s trigger=%s\n' "$(date -Is)" "$SNAP" "$TRIGGER" \
  >>"${CLAUDE_HOOK_LOG_DIR:-$HOME/.claude/hook-logs}/precompact.log" 2>/dev/null || true
exit 0
