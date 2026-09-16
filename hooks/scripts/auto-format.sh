#!/usr/bin/env bash
# auto-format.sh — formata o arquivo que o agente acabou de escrever/editar.
#
# Evento:  post_tool_call (Hermes) / PostToolUse (Claude Code, Cursor)
# Contrato: exit 0 sempre. Nunca bloqueia nada — só formata e sai.
#
# Usa o formatador do PRÓPRIO projeto quando existir (node_modules/.bin,
# venv, config local) e cai para o global. Se não houver formatador para
# a extensão, não faz nada. Falhas são silenciosas por design: um formatador
# quebrado não pode derrubar a sessão do agente.
set -u

payload=$(cat)

path=$(printf '%s' "$payload" | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    raise SystemExit
ti = d.get("tool_input") or {}
if not isinstance(ti, dict):
    ti = {}
for k in ("file_path", "path", "filePath", "target_file"):
    v = ti.get(k)
    if isinstance(v, str) and v.strip():
        print(v)
        break
' 2>/dev/null)

[ -z "${path:-}" ] && exit 0
[ -f "$path" ] || exit 0

run() { command -v "$1" >/dev/null 2>&1 && timeout 15 "$@" >/dev/null 2>&1; }

# binário local do projeto tem prioridade sobre o global
local_bin() {
  d=$(dirname "$path")
  while [ "$d" != "/" ] && [ -n "$d" ]; do
    [ -x "$d/node_modules/.bin/$1" ] && { echo "$d/node_modules/.bin/$1"; return 0; }
    [ -x "$d/.venv/bin/$1" ] && { echo "$d/.venv/bin/$1"; return 0; }
    [ -x "$d/venv/bin/$1" ] && { echo "$d/venv/bin/$1"; return 0; }
    d=$(dirname "$d")
  done
  return 1
}

ext="${path##*.}"
case "$ext" in
  js|jsx|ts|tsx|mjs|cjs|json|jsonc|css|scss|less|html|vue|svelte|md|yaml|yml)
    if b=$(local_bin prettier); then timeout 15 "$b" --write "$path" >/dev/null 2>&1
    elif b=$(local_bin biome); then timeout 15 "$b" format --write "$path" >/dev/null 2>&1
    elif [ -x "$(git rev-parse --show-toplevel 2>/dev/null)/node_modules/.bin/prettier" ]; then
      timeout 15 "$(git rev-parse --show-toplevel)/node_modules/.bin/prettier" --write "$path" >/dev/null 2>&1
    else run prettier --write "$path" || run biome format --write "$path" || true
    fi ;;
  py)
    if b=$(local_bin ruff); then timeout 15 "$b" format "$path" >/dev/null 2>&1
    elif b=$(local_bin black); then timeout 15 "$b" -q "$path" >/dev/null 2>&1
    else run ruff format "$path" || run black -q "$path" || true
    fi ;;
  go)   run gofmt -w "$path" ;;
  rs)   run rustfmt "$path" ;;
  sh|bash|zsh|ksh) run shfmt -w -i 2 "$path" ;;
  lua)  run stylua "$path" ;;
  gd)   run gdformat "$path" ;;
  c|h|cpp|hpp|cc|hh) run clang-format -i "$path" ;;
  java) run google-java-format -i "$path" ;;
  kt|kts) run ktlint -F "$path" ;;
  cs)   run dotnet format --include "$path" >/dev/null 2>&1 ;;
  php)  run php-cs-fixer fix "$path" ;;
  rb)   run rubocop -a "$path" ;;
  swift) run swift-format -i "$path" ;;
  nix)  run nixfmt "$path" ;;
esac

exit 0
