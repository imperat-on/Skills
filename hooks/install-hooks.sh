#!/usr/bin/env bash
# install-hooks.sh — liga os hooks deste kit nas CLIs detectadas.
#
#   ./install-hooks.sh                 # instala o que der, mostra o que falta
#   ./install-hooks.sh --only claude   # uma CLI só (claude|codex|hermes|opencode|prime|cursor)
#   ./install-hooks.sh --dry-run       # mostra o que faria
#
# Sempre faz backup do arquivo de config antes de tocar nele (*.bak-<timestamp>).
# Nada aqui instala hooks que possam queimar trabalho sem você ver: revise os
# scripts em scripts/ antes.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOOKS="$REPO/hooks/scripts"
CFG="$REPO/hooks/configs"
STAMP="$(date +%Y%m%d%H%M%S)"
ONLY=""
DRY=0

while [ $# -gt 0 ]; do
  case "$1" in
    --only) ONLY="${2:?}"; shift 2 ;;
    --dry-run) DRY=1; shift ;;
    -h|--help) sed -n '2,12p' "$0"; exit 0 ;;
    *) echo "flag desconhecida: $1" >&2; exit 2 ;;
  esac
done

want() { [ -z "$ONLY" ] || [ "$ONLY" = "$1" ]; }
say() { printf '  %s\n' "$*"; }
do_it() { [ "$DRY" = "1" ] && say "DRY  $*" || eval "$*"; }
backup() { [ -e "$1" ] && [ "$DRY" != "1" ] && cp -a "$1" "$1.bak-$STAMP" && say "backup: $1.bak-$STAMP"; return 0; }

# chmod defensivo: os hooks precisam ser executáveis
[ "$DRY" = "1" ] || chmod +x "$HOOKS"/*.sh "$HOOKS"/*.py 2>/dev/null || true

echo "hooks deste kit: $HOOKS"
echo

# ---------------------------------------------------------------- Claude Code
if want claude; then
  echo "== Claude Code  (~/.claude/settings.json)"
  [ -d "$HOME/.claude" ] || say "~/.claude nao existe (CLI nao instalada?)"
  if [ -d "$HOME/.claude" ]; then
    if [ "$DRY" = "1" ]; then
      say "faria merge de $(basename "$CFG/claude.settings.hooks.json") em ~/.claude/settings.json"
    else
      backup "$HOME/.claude/settings.json"
      python3 - "$HOME/.claude/settings.json" "$CFG/claude.settings.hooks.json" "$HOOKS" <<'PY'
import json, os, sys
target, template, hooks = sys.argv[1], sys.argv[2], sys.argv[3]
cfg = json.load(open(target)) if os.path.exists(target) else {}
new = json.load(open(template))
def sub(o):
    if isinstance(o, str):  return o.replace("__HOOKS__", hooks)
    if isinstance(o, dict): return {k: sub(v) for k, v in o.items()}
    if isinstance(o, list): return [sub(v) for v in o]
    return o
new = sub(new); new.pop("$comment", None)
merged = cfg.setdefault("hooks", {})
added = 0
for event, groups in new["hooks"].items():
    bucket = merged.setdefault(event, [])
    for g in groups:
        if g not in bucket:
            bucket.append(g); added += 1
json.dump(cfg, open(target, "w"), indent=2, ensure_ascii=False)
print(f"   {added} grupo(s) de hook adicionados em {target}")
PY
    fi
  fi
fi

# ---------------------------------------------------------------------- Codex
if want codex; then
  echo "== Codex CLI  (~/.codex/hooks.json)"
  if [ -d "$HOME/.codex" ]; then
    if [ "$DRY" = "1" ]; then
      say "escreveria ~/.codex/hooks.json"
    else
      backup "$HOME/.codex/hooks.json"
      sed "s|__HOOKS__|$HOOKS|g" "$CFG/codex.hooks.json" > "$HOME/.codex/hooks.json"
      say "escrito: ~/.codex/hooks.json"
      say "PENDENTE: rode 'codex' e execute /hooks para confiar nos hooks (o Codex guarda o hash de cada um)"
    fi
  else
    say "~/.codex nao existe (Codex nao instalado?)"
  fi
fi

# --------------------------------------------------------------------- Hermes
if want hermes; then
  echo "== Hermes Agent  (~/.hermes/config.yaml)"
  CFGY="$HOME/.hermes/config.yaml"
  if [ ! -f "$CFGY" ]; then
    say "~/.hermes/config.yaml nao encontrado"
  elif grep -qE '^hooks:' "$CFGY"; then
    say "já existe um bloco 'hooks:' em $CFGY — não toquei nele."
    say "mescle manualmente o conteúdo de hooks/configs/hermes.config.snippet.yaml"
  elif [ "$DRY" = "1" ]; then
    say "anexaria o bloco de hooks em ~/.hermes/config.yaml"
  else
    backup "$CFGY"
    {
      printf '\n# --- hooks do kit Skills (%s) ---\n' "$(date +%Y-%m-%d)"
      sed "s|__HOOKS__|$HOOKS|g" "$CFG/hermes.config.snippet.yaml" | grep -v '^#'
    } >> "$CFGY"
    say "bloco de hooks anexado em ~/.hermes/config.yaml"
    say "valide com:  hermes hooks test"
  fi
fi

# ------------------------------------------------------------------- OpenCode
if want opencode; then
  echo "== OpenCode  (~/.config/opencode/plugins/)"
  D="$HOME/.config/opencode/plugins"
  if [ -d "$HOME/.config/opencode" ] || [ -d "$HOME/.opencode" ]; then
    do_it "mkdir -p '$D'"
    do_it "sed 's|__HOOKS__|$HOOKS|g' '$CFG/opencode.agent-guards.js' > '$D/agent-guards.js'"
    say "plugin em $D/agent-guards.js (reinicie o OpenCode)"
  else
    say "OpenCode nao detectado"
  fi
fi

# ----------------------------------------------------------------- Prime Agent
if want prime; then
  echo "== Prime Agent  (~/.prime/agent/extensions/)"
  D="$HOME/.prime/agent/extensions"
  if [ -d "$HOME/.prime/agent" ]; then
    do_it "mkdir -p '$D'"
    do_it "sed 's|__HOOKS__|$HOOKS|g' '$CFG/prime-agent.agent-guards.ts' > '$D/agent-guards.ts'"
    say "extensão em $D/agent-guards.ts (rode /reload no Prime Agent)"
  else
    say "Prime Agent nao detectado"
  fi
fi

# --------------------------------------------------------------------- Cursor
if want cursor; then
  echo "== Cursor  (~/.cursor/hooks.json)"
  if [ -d "$HOME/.cursor" ]; then
    if [ "$DRY" = "1" ]; then
      say "escreveria ~/.cursor/hooks.json"
    else
      backup "$HOME/.cursor/hooks.json"
      sed "s|__HOOKS__|$HOOKS|g" "$CFG/cursor.hooks.json" > "$HOME/.cursor/hooks.json"
      say "escrito ~/.cursor/hooks.json (schema NÃO conferido na doc oficial — teste)"
    fi
  else
    say "~/.cursor nao existe"
  fi
fi

echo
echo "logs de auditoria:  ${XDG_STATE_HOME:-$HOME/.local/state}/skills-kit/audit.jsonl"
echo "teste dos scripts:  bash $REPO/tools/test-hooks.sh"
