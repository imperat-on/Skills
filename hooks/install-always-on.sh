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

# Reescreve o arquivo com o bloco exatamente uma vez. Feito em Python para o
# resultado ser byte-a-byte estável: rodar duas vezes tem que dar o MESMO arquivo
# (a versão em awk/sed acrescentava 1 byte por execução).
build_with_block() { # <arquivo> <tmp> <titulo>
  local f="$1" tmp="$2" title="$3"
  SKILLS_KIT_FILE="$f" SKILLS_KIT_BLOCK="$BLOCK" SKILLS_KIT_TITLE="$title" SKILLS_KIT_TMP="$tmp"   python3 - <<'PY'
import os, pathlib, re
f = pathlib.Path(os.environ["SKILLS_KIT_FILE"])
block = pathlib.Path(os.environ["SKILLS_KIT_BLOCK"]).read_text(encoding="utf-8").strip() + "\n"
out = pathlib.Path(os.environ["SKILLS_KIT_TMP"])
t = f.read_text(encoding="utf-8") if f.exists() else ""
t = re.sub(r"<!-- skills-kit:always-on -->.*?<!-- /skills-kit:always-on -->\n?", "", t, flags=re.S)
t = t.rstrip()
if not t:
    t = os.environ["SKILLS_KIT_TITLE"]
out.write_text(t.rstrip() + "\n\n" + block, encoding="utf-8")
PY
}

strip_block() { # <arquivo> <tmp>
  local f="$1" tmp="$2"
  SKILLS_KIT_FILE="$f" SKILLS_KIT_TMP="$tmp" python3 - <<'PY'
import os, pathlib, re
f = pathlib.Path(os.environ["SKILLS_KIT_FILE"])
t = re.sub(r"<!-- skills-kit:always-on -->.*?<!-- /skills-kit:always-on -->\n?", "",
           f.read_text(encoding="utf-8"), flags=re.S).rstrip()
pathlib.Path(os.environ["SKILLS_KIT_TMP"]).write_text((t + "\n") if t else "", encoding="utf-8")
PY
}

apply_block() { # <arquivo> <cli>
  local f="$1" cli="$2" tmp
  tmp="$(mktemp)"
  build_with_block "$f" "$tmp" "# Instruções globais — $(basename "$(dirname "$f")")"
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
  strip_block "$f" "$f.tmp"
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
      elif [ -n "$sd" ] && find "$sd" -maxdepth 3 \( -type d -o -type l \) -name "$s" 2>/dev/null | grep -q .; then :
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
