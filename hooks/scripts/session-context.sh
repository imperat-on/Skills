#!/usr/bin/env bash
# session-context.sh — injeta o estado do repositório no início da sessão.
#
# Evento:  on_session_start (Hermes) / SessionStart (Claude Code)
# Contrato: imprime JSON no stdout. A forma do JSON depende do host, então o
# script detecta o host pelo payload (Claude Code manda "transcript_path").
#   Hermes       -> {"context": "..."}
#   Claude Code  -> {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "..."}}
# Force o dialeto com SKILLS_KIT_STYLE=hermes|claude se a detecção errar.
set -u

payload=$(cat)
[ -z "${payload// /}" ] && exit 0

cwd=$(printf '%s' "$payload" | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    print(""); raise SystemExit
print(d.get("cwd") or d.get("working_directory") or "")
' 2>/dev/null)
[ -z "${cwd:-}" ] && cwd="$PWD"
cd "$cwd" 2>/dev/null || exit 0

style="${SKILLS_KIT_STYLE:-}"
if [ -z "$style" ]; then
  case "$payload" in
    *'"transcript_path"'*) style="claude" ;;
    *) style="hermes" ;;
  esac
fi

ctx=""
add() { ctx="${ctx}${1}
"; }

if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  add "## Estado do repositório"
  add "branch: $(git rev-parse --abbrev-ref HEAD 2>/dev/null)"
  add "HEAD: $(git log -1 --format='%h %s' 2>/dev/null)"
  if [ -n "$(git status --porcelain 2>/dev/null | head -1)" ]; then
    n=$(git status --porcelain 2>/dev/null | wc -l | tr -d ' ')
    add "working tree: $n arquivo(s) modificado(s) não commitados"
    add "lista:"
    add "$(git status --short 2>/dev/null | head -15)"
  else
    add "working tree: limpo"
  fi
  add "últimos commits:"
  add "$(git log --oneline -5 2>/dev/null)"
fi

for f in AGENTS.md CLAUDE.md GEMINI.md CONTRIBUTING.md; do
  [ -f "$f" ] && add "regras do projeto em $f (leia antes de editar)"
done
for d in .claude/skills .agents/skills .opencode/skills .prime/agent/skills; do
  if [ -d "$d" ]; then add "há skills locais do repositório em $d"; break; fi
done

last=$(git log -1 --format=%ct 2>/dev/null || echo 0)
[ "$last" != "0" ] && add "última atividade no repo: $(date -d "@$last" '+%Y-%m-%d %H:%M' 2>/dev/null || echo '?')"

SKILLS_KIT_CTX="$ctx" python3 - "$style" <<'PY'
import json, os, sys
ctx = os.environ.get("SKILLS_KIT_CTX", "")
style = sys.argv[1]
if style == "claude":
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart",
                                             "additionalContext": ctx}}))
else:
    print(json.dumps({"context": ctx}))
PY
