#!/usr/bin/env bash
# install-mcp.sh — instala os MCPs do kit em cada CLI detectada, usando o comando
# OFICIAL de cada uma (nada de editar config na mão), com backup e reversível.
#
#   ./install-mcp.sh                        # conjunto "light" (4 servidores)
#   ./install-mcp.sh --set hermes           # os 9 que estão no Hermes
#   ./install-mcp.sh --set all              # os 13 do catálogo
#   ./install-mcp.sh --names context7,time  # escolher na mão
#   ./install-mcp.sh --only codex           # uma CLI (claude|codex|opencode|prime|hermes)
#   ./install-mcp.sh --dry-run              # mostra os comandos, não executa
#   ./install-mcp.sh --remove               # desinstala o conjunto informado
#
# Por que "light" é o default: cada servidor MCP entra em TODA chamada da API.
# Os 9 do Hermes são 104 ferramentas; playwright + chrome-devtools sozinhos são
# 55 delas. Instale caro só onde você usa.
#
# Fonte única da verdade: mcp/servers.json (comando, args e env de cada servidor).
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVERS="$REPO/mcp/servers.json"
STAMP="$(date +%Y%m%d%H%M%S)"
SET="light"
NAMES=""
ONLY=""
DRY=0
REMOVE=0

while [ $# -gt 0 ]; do
  case "$1" in
    --set) SET="${2:?light|hermes|all}"; shift 2 ;;
    --names) NAMES="${2:?lista separada por virgula}"; shift 2 ;;
    --only) ONLY="${2:?}"; shift 2 ;;
    --dry-run) DRY=1; shift ;;
    --remove) REMOVE=1; shift ;;
    -h|--help) sed -n '2,20p' "$0"; exit 0 ;;
    *) echo "flag desconhecida: $1" >&2; exit 2 ;;
  esac
done

[ -f "$SERVERS" ] || { echo "nao achei $SERVERS" >&2; exit 1; }

case "$SET" in
  light)  DEF="context7,time,fetch,git" ;;
  hermes) DEF="context7,time,fetch,git,memory,sequential-thinking,filesystem,playwright,chrome-devtools" ;;
  all)    DEF="context7,time,fetch,git,memory,sequential-thinking,filesystem,playwright,chrome-devtools,github,sentry,figma,everything" ;;
  *)      echo "conjunto desconhecido: $SET" >&2; exit 2 ;;
esac
WANT="${NAMES:-$DEF}"

# name \t command \t args \t env(K=V,K=V)  — só servidores stdio (remote tem URL, não comando)
tsv="$(python3 - "$SERVERS" "$WANT" <<'PY'
import json, sys
servers = json.load(open(sys.argv[1]))["servers"]
want = [w.strip() for w in sys.argv[2].split(",") if w.strip()]
for name in want:
    s = servers.get(name)
    if not s:
        print(f"#FALTANDO\t{name}\t\t", end="\n"); continue
    cmd = s.get("command") or []
    if not cmd:
        print(f"#SEMCOMANDO\t{name}\t\t", end="\n"); continue
    env = ",".join(
        f"{k}={v}" for k, v in (s.get("env") or {}).items()
        if not str(v).startswith("<")          # placeholder: usuário preenche depois
    )
    print("\t".join([name, cmd[0], " ".join(cmd[1:]), env]))
PY
)"

run() { # executa ou mostra
  if [ "$DRY" = "1" ]; then echo "    DRY  $*"; else eval "$@"; fi
}

detect() { # binário -> existe?
  command -v "$1" >/dev/null 2>&1
}

install_one() { # <cli> <name> <cmd> <args> <env>
  local cli="$1" name="$2" cmd="$3" args="$4" env="$5" eflag=() kv envpart=""
  if [ -n "$env" ]; then
    IFS=',' read -ra _pairs <<< "$env"
    for kv in "${_pairs[@]}"; do eflag+=("$kv"); done
  fi
  [ ${#eflag[@]} -gt 0 ] && envpart="$(printf -- '-e %q ' "${eflag[@]}")"
  case "$cli" in
    claude)
      run "claude mcp add --scope user '$name' ${envpart}-- $cmd $args"
      ;;
    codex)
      run "codex mcp add '$name' -- $cmd $args"
      ;;
    prime)
      run "prime-agent mcp add '$name' -- $cmd $args"
      ;;
    hermes)
      run "hermes mcp add '$name' --command $cmd --args $args"
      ;;
    opencode)
      # OpenCode não tem add não-interativo para stdio: edita o config (com backup).
      run "python3 '$REPO/mcp/opencode-mcp-edit.py' add '$name' '$cmd' '$args' '$env'"
      ;;
  esac
}

remove_one() { # <cli> <name>
  local cli="$1" name="$2"
  case "$cli" in
    claude)   run "claude mcp remove --scope user '$name'" ;;
    codex)    run "codex mcp remove '$name'" ;;
    prime)    run "prime-agent mcp remove '$name'" ;;
    hermes)   run "hermes mcp remove '$name'" ;;
    opencode) run "python3 '$REPO/mcp/opencode-mcp-edit.py' remove '$name'" ;;
  esac
}

echo "conjunto: $SET  ($WANT)"
echo "modo:     $([ "$REMOVE" = 1 ] && echo remover || echo instalar)$([ "$DRY" = 1 ] && echo ' (dry-run)')"
echo

for cli in claude codex opencode prime hermes; do
  [ -n "$ONLY" ] && [ "$ONLY" != "$cli" ] && continue
  # a CLI existe nesta máquina?
  case "$cli" in
    claude)   detect claude || { echo "== claude: nao instalado, pulando"; continue; } ;;
    codex)    detect codex || { echo "== codex: nao instalado, pulando"; continue; } ;;
    opencode) detect opencode || { echo "== opencode: nao instalado, pulando"; continue; } ;;
    prime)    detect prime-agent || { echo "== prime: nao instalado, pulando"; continue; } ;;
    hermes)   detect hermes || { echo "== hermes: nao instalado, pulando"; continue; } ;;
  esac
  echo "== $cli"
  while IFS=$'\t' read -r name cmd args env; do
    [ -z "$name" ] && continue
    case "$name" in
      '#FALTANDO')   echo "    ?  $cmd nao esta em servers.json"; continue ;;
      '#SEMCOMANDO') echo "    -  $cmd e remoto (precisa de URL/token) — instale a mao"; continue ;;
    esac
    if [ "$REMOVE" = 1 ]; then remove_one "$cli" "$name"
    else install_one "$cli" "$name" "$cmd" "$args" "$env"; fi
  done <<< "$tsv"
  echo
done

echo "Conferir depois:"
echo "  claude mcp list | codex mcp list | opencode mcp list | prime-agent mcp list | hermes mcp list"
[ "$DRY" = 1 ] || echo "Desfazer: $0 --remove --set $SET"
