#!/usr/bin/env bash
# install.sh — instala este kit de skills nas CLIs de código presentes na máquina.
#
# Uso:
#   ./install.sh                    # detecta CLIs, instala o tier core (symlink)
#   ./install.sh --tier all         # instala as 117 skills
#   ./install.sh --copy             # copia em vez de symlinkar
#   ./install.sh --target claude    # só numa CLI (pode repetir a flag)
#   ./install.sh --list             # mostra o que seria instalado e onde
#   ./install.sh --dry-run          # não escreve nada, só mostra
#   ./install.sh --force            # sobrescreve skill já existente no destino
#   ./install.sh --hooks            # instala também os hooks (ver hooks/README.md)
#   ./install.sh --uninstall        # remove os symlinks que este script criou
#
# Sem dependências além de bash, python3 e coreutils.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MANIFEST="$REPO/manifest.json"
TIER="core"
MODE="link"
FORCE=0
DRY=0
LIST=0
UNINSTALL=0
DO_HOOKS=0
TARGETS=()

while [ $# -gt 0 ]; do
  case "$1" in
    --tier) TIER="${2:?--tier precisa de valor: core|all}"; shift 2 ;;
    --tier=*) TIER="${1#*=}"; shift ;;
    --copy) MODE="copy"; shift ;;
    --link) MODE="link"; shift ;;
    --force) FORCE=1; shift ;;
    --dry-run) DRY=1; shift ;;
    --list) LIST=1; shift ;;
    --uninstall) UNINSTALL=1; shift ;;
    --hooks) DO_HOOKS=1; shift ;;
    --target) TARGETS+=("${2:?--target precisa de valor}"); shift 2 ;;
    --target=*) TARGETS+=("${1#*=}"); shift ;;
    -h|--help) sed -n '2,20p' "$0"; exit 0 ;;
    *) echo "flag desconhecida: $1" >&2; exit 2 ;;
  esac
done

case "$TIER" in core|all) ;; *) echo "--tier invalido: $TIER (use core|all)" >&2; exit 2 ;; esac
[ -f "$MANIFEST" ] || { echo "manifest.json nao encontrado em $REPO" >&2; exit 1; }

# ---- destinos por CLI -------------------------------------------------------
# Fontes: docs oficiais de cada CLI (ver REPORT.md, secao 5).
declare -A DEST=(
  [agents]="$HOME/.agents/skills"          # Codex, OpenCode, Prime Agent, Gemini CLI, Cursor, Crush
  [claude]="$HOME/.claude/skills"          # Claude Code (também lido por OpenCode/Crush/Prime)
  [hermes]="$HOME/.hermes/skills"          # Hermes Agent (mantém subpasta por categoria)
  [prime]="$HOME/.prime/agent/skills"      # Prime Agent (path nativo, além do ~/.agents/skills)
  [opencode]="$HOME/.config/opencode/skills"
  [crush]="$HOME/.config/crush/skills"
  [cursor]="$HOME/.cursor/skills"
  [gemini]="$HOME/.gemini/skills"
)
# binário presente -> destino usado. `agents` é o diretório compartilhado pela
# convenção Agent Skills, então Codex/OpenCode/Prime caem nele por padrão.
declare -A PROBE_BIN=(
  [claude]="claude"
  [codex]="codex"
  [opencode]="opencode"
  [prime-agent]="prime-agent"
  [hermes]="hermes"
  [crush]="crush"
  [cursor-agent]="cursor-agent"
  [gemini]="gemini"
)
declare -A PROBE_DEST=(
  [claude]="claude"
  [codex]="agents"
  [opencode]="agents"
  [prime-agent]="agents"
  [hermes]="hermes"
  [crush]="crush"
  [cursor-agent]="cursor"
  [gemini]="agents"
)

STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/skills-kit"
STATE_FILE="$STATE_DIR/installed.list"

TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
python3 - "$MANIFEST" "$TIER" > "$TMP/list.tsv" <<'PY'
import json, sys
man, tier = json.load(open(sys.argv[1])), sys.argv[2]
for s in man["skills"]:
    if tier == "core" and s["tier"] != "core":
        continue
    print(f'{s["category"]}\t{s["name"]}')
PY

TOTAL=$(wc -l < "$TMP/list.tsv")

# ---- decide os destinos -----------------------------------------------------
if [ ${#TARGETS[@]} -gt 0 ]; then
  SELECTED=("${TARGETS[@]}")
else
  SELECTED=()
  any=0
  for bin in claude codex opencode prime-agent hermes crush cursor-agent gemini; do
    if command -v "$bin" >/dev/null 2>&1; then
      SELECTED+=("${PROBE_DEST[$bin]}")
      echo "detectado: $bin -> ${PROBE_DEST[$bin]}"
      any=1
    fi
  done
  [ "$any" = "0" ] && { SELECTED=("agents"); echo "nenhuma CLI detectada no PATH; usando ~/.agents/skills"; }
fi
# dedup
readarray -t SELECTED < <(printf '%s\n' "${SELECTED[@]}" | awk '!x[$0]++')

echo "repo:    $REPO"
echo "tier:    $TIER  ($TOTAL skills)"
echo "modo:    $MODE"
echo "destino: ${SELECTED[*]}"
echo

if [ "$LIST" = "1" ]; then
  for t in "${SELECTED[@]}"; do
    d="${DEST[$t]:-}"
    [ -n "$d" ] || { echo "  ! target desconhecido: $t" >&2; continue; }
    echo "== $t  ->  $d"
    while IFS=$'\t' read -r cat name; do
      [ "$t" = "hermes" ] && echo "   $cat/$name" || echo "   $name"
    done < "$TMP/list.tsv"
  done
  exit 0
fi

# ---- uninstall --------------------------------------------------------------
if [ "$UNINSTALL" = "1" ]; then
  if [ ! -f "$STATE_FILE" ]; then echo "nada a remover ($STATE_FILE ausente)"; exit 0; fi
  n=0
  while read -r p; do
    case "$(readlink "$p" 2>/dev/null || true)" in
      "$REPO"/*) rm -f "$p"; n=$((n+1)) ;;
    esac
  done < <(sort -r "$STATE_FILE")
  rm -f "$STATE_FILE"
  echo "removidos: $n"
  exit 0
fi

# ---- instala ----------------------------------------------------------------
created=0; skipped=0
for t in "${SELECTED[@]}"; do
  root="${DEST[$t]:-}"
  if [ -z "$root" ]; then echo "! target desconhecido: $t (ignore)" >&2; continue; fi
  echo "== $t -> $root"
  [ "$DRY" = "1" ] || mkdir -p "$root"
  while IFS=$'\t' read -r cat name; do
    src="$REPO/skills/$cat/$name"
    if [ "$t" = "hermes" ]; then dst="$root/$cat/$name"; else dst="$root/$name"; fi
    if [ -e "$dst" ] || [ -L "$dst" ]; then
      if [ "$FORCE" != "1" ]; then skipped=$((skipped+1)); continue; fi
      [ "$DRY" = "1" ] || rm -rf "$dst"
    fi
    if [ "$DRY" = "1" ]; then
      echo "   + $dst"
    else
      [ "$MODE" = "copy" ] && { mkdir -p "$(dirname "$dst")"; cp -r "$src" "$dst"; } \
                           || { mkdir -p "$(dirname "$dst")"; ln -s "$src" "$dst"; }
      mkdir -p "$STATE_DIR"; echo "$dst" >> "$STATE_FILE"
    fi
    created=$((created+1))
  done < "$TMP/list.tsv"
done

echo
echo "instalado: $created   pulado (ja existia): $skipped"
[ "$skipped" != "0" ] && echo "use --force para sobrescrever os pulados"

if [ "$DO_HOOKS" = "1" ]; then
  echo
  if [ "$DRY" = "1" ]; then
    bash "$REPO/hooks/install-hooks.sh" --dry-run
  else
    bash "$REPO/hooks/install-hooks.sh"
  fi
fi

cat <<'EOF'

Proximo passo: abra uma sessao NOVA na CLI (o indice de skills e lido no start)
e rode:
  skills_list          # Hermes
  /skills              # Claude Code / Codex
Depois confirme que aparecem os nomes listados no CATALOG.md.
EOF
