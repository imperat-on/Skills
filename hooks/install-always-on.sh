#!/usr/bin/env bash
# install-always-on.sh — deixa ponytail (lazy senior) e caveman ativos SEMPRE,
# em toda sessão, em cada CLI instalada na máquina.
#
# Como: escreve um bloco com marcador no arquivo de instrução permanente de cada
# CLI — o arquivo que ela lê no começo de TODA sessão. É idempotente (rodar de
# novo substitui o bloco, não duplica), faz backup e é reversível (--remove).
#
#   ./install-always-on.sh                # todas as CLIs detectadas
#   ./install-always-on.sh --only claude  # claude|codex|opencode|prime|hermes
#   ./install-always-on.sh --dry-run      # mostra sem escrever
#   ./install-always-on.sh --remove       # tira o bloco (restaura o arquivo)
#
# O texto do bloco mora em hooks/always-on.md (fonte única).
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BLOCK="$REPO/hooks/always-on.md"
START='<!-- skills-kit:always-on -->'
END='<!-- /skills-kit:always-on -->'
STAMP="$(date +%Y%m%d%H%M%S)"
ONLY=""
DRY=0
REMOVE=0

while [ $# -gt 0 ]; do
  case "$1" in
    --only) ONLY="${2:?}"; shift 2 ;;
    --dry-run) DRY=1; shift ;;
    --remove) REMOVE=1; shift ;;
    -h|--help) sed -n '2,12p' "$0"; exit 0 ;;
    *) echo "flag desconhecida: $1" >&2; exit 2 ;;
  esac
done

[ -f "$BLOCK" ] || { echo "nao achei $BLOCK" >&2; exit 1; }

# CLI -> arquivo de instrução permanente.
# Fontes: docs de cada produto (ver REPORT.md §5).
target_file() {
  case "$1" in
    claude)   echo "$HOME/.claude/CLAUDE.md" ;;            # Claude Code: user memory
    codex)    if [ -f "$HOME/.codex/AGENTS.override.md" ]; then
                echo "$HOME/.codex/AGENTS.override.md"      # precedência sobre AGENTS.md
              else
                echo "$HOME/.codex/AGENTS.md"
              fi ;;
    opencode) echo "$HOME/.config/opencode/AGENTS.md" ;;   # regras globais
    prime)    echo "$HOME/.prime/agent/AGENTS.md" ;;       # instruções globais
    hermes)   echo "$HOME/.hermes/SOUL.md" ;;              # identity slot #1
    *)        echo "" ;;
  esac
}

# onde as skills daquele CLI vivem (para avisar se as duas skills não estão instaladas)
skills_dir() {
  case "$1" in
    claude)   echo "$HOME/.claude/skills" ;;
    codex)    echo "$HOME/.agents/skills" ;;
    opencode) echo "$HOME/.agents/skills" ;;
    prime)    echo "$HOME/.agents/skills" ;;
    hermes)   echo "$HOME/.hermes/skills" ;;
    *)        echo "" ;;
  esac
}

apply_block() { # <arquivo> <cli>
  local f="$1" cli="$2" tmp
  tmp="$(mktemp)"
  if [ ! -e "$f" ]; then
    # arquivo novo: começa com um título para não virar um .md órfão
    { echo "# Instruções globais — $(basename "$(dirname "$f")")"; echo; } > "$tmp"
    cat "$BLOCK" >> "$tmp"
  elif grep -qF "$START" "$f"; then
    # já existe: substitui o bloco inteiro (idempotente)
    awk -v s="$START" -v e="$END" '
      $0 == s {skip=1; next}
      $0 == e {skip=0; next}
      !skip {print}
    ' "$f" > "$tmp"
    printf '\n' >> "$tmp"
    cat "$BLOCK" >> "$tmp"
  else
    cat "$f" > "$tmp"
    printf '\n' >> "$tmp"
    cat "$BLOCK" >> "$tmp"
  fi
  if [ "$DRY" = "1" ]; then
    echo "  DRY  escreveria $(wc -c < "$tmp") bytes em $f"
  else
    mkdir -p "$(dirname "$f")"
    [ -e "$f" ] && cp -a "$f" "$f.bak-$STAMP" && echo "  backup: $f.bak-$STAMP"
    mv "$tmp" "$f"
    echo "  ok: $cli -> $f ($(wc -c < "$f") bytes)"
  fi
  rm -f "$tmp"
}

remove_block() { # <arquivo>
  local f="$1"
  [ -f "$f" ] || return 0
  grep -qF "$START" "$f" || return 0
  if [ "$DRY" = "1" ]; then echo "  DRY  removeria o bloco de $f"; return 0; fi
  cp -a "$f" "$f.bak-$STAMP"
  awk -v s="$START" -v e="$END" '$0 == s {skip=1; next} $0 == e {skip=0; next} !skip {print}' "$f" > "$f.tmp"
  mv "$f.tmp" "$f"
  # se o arquivo ficou vazio (só o bloco), remove
  if [ ! -s "$f" ] || [ "$(tr -d '[:space:]' < "$f" | wc -c)" = "0" ]; then rm -f "$f"; echo "  removido (arquivo ficou vazio): $f"; else echo "  bloco removido de $f"; fi
}

echo "bloco: $BLOCK"
echo
installed=0
for cli in claude codex opencode prime hermes; do
  [ -n "$ONLY" ] && [ "$ONLY" != "$cli" ] && continue
  # só mexe na CLI que existe de fato
  case "$cli" in
    claude)   [ -d "$HOME/.claude" ] || continue ;;
    codex)    [ -d "$HOME/.codex" ] || continue ;;
    opencode) [ -d "$HOME/.config/opencode" ] || continue ;;
    prime)    [ -d "$HOME/.prime/agent" ] || continue ;;
    hermes)   [ -d "$HOME/.hermes" ] || continue ;;
  esac
  f="$(target_file "$cli")"
  [ -n "$f" ] || continue
  echo "== $cli"
  if [ "$REMOVE" = "1" ]; then
    remove_block "$f"
  else
    apply_block "$f" "$cli"
    # as duas skills existem para essa CLI?
    sd="$(skills_dir "$cli")"
    for s in ponytail caveman; do
      if [ -n "$sd" ] && [ -d "$sd/$s" ]; then :
      elif [ -n "$sd" ] && find "$sd" -maxdepth 3 -type d -name "$s" 2>/dev/null | grep -q .; then :
      else echo "  aviso: skill '$s' nao esta instalada em $sd — rode ./install.sh --tier all"; fi
    done
    installed=$((installed+1))
  fi
done

echo
if [ "$REMOVE" = "1" ]; then
  echo "bloco removido. Reinicie as sessoes para valer."
else
  echo "$installed CLI(s) configuradas. Abra uma sessao NOVA em cada uma."
  echo "Conferir: abra a CLI e pergunte 'quais modos estao ativos?' — ela deve citar ponytail e caveman."
fi
