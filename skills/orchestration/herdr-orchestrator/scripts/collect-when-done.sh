#!/bin/bash
# collect-when-done.sh — espera os agentes ficarem ociosos e captura o output final de cada um.
#
# Problema que resolve: quem orquestra fica refem de alguem avisar que o worker terminou.
# Este script poll o runtime do Herdr, espera TODO agente da lista sair de "working"
# (nunca confunde "ainda nao comecou" com "terminou": exige que ao menos um tenha sido
# visto trabalhando, a menos que --ja-idle seja passado), captura o bloco final de cada
# um (DONE/BLOCKED/FAILED/NEEDS_INPUT + campos) e SAI — para que um
# `terminal(background=true, notify=true)` entregue a notificacao de conclusao.
#
# Uso:
#   collect-when-done.sh -r <run-id> -a agente1,agente2 [-a agente3] [-o dir] [-t timeout_s] [-i intervalo_s]
# Saida:
#   <dir>/<agente>.raw.txt    saida recente completa
#   <dir>/<agente>.final.txt  bloco final do worker (o relatorio)
#   <dir>/RESUMO.md           resumo com todos os blocos + estado dos agentes
set -u

RUN=""
AGENTES=()
OUT=""
TIMEOUT=7200
INTERVALO=30
JA_IDLE=0
while [ $# -gt 0 ]; do
  case "$1" in
  -r)
    RUN="$2"
    shift 2
    ;;
  -a)
    IFS=',' read -ra tmp <<<"$2"
    AGENTES+=("${tmp[@]}")
    shift 2
    ;;
  -o)
    OUT="$2"
    shift 2
    ;;
  -t)
    TIMEOUT="$2"
    shift 2
    ;;
  -i)
    INTERVALO="$2"
    shift 2
    ;;
  --ja-idle)
    JA_IDLE=1
    shift
    ;;
  *)
    echo "arg desconhecido: $1" >&2
    exit 2
    ;;
  esac
done
[ -n "$RUN" ] && [ ${#AGENTES[@]} -gt 0 ] || {
  echo "uso: $0 -r <run-id> -a a1,a2 [-o dir] [-t s] [-i s]" >&2
  exit 2
}
OUT="${OUT:-/tmp/orch-collect/$RUN}"
mkdir -p "$OUT"
LOG="$OUT/coletor.log"

status_de() { # $1 = agente -> working|idle|blocked|unknown
  timeout 25 herdr agent list 2>/dev/null | python3 -c "
import json,sys
alvo='$1'
try:
    d=json.load(sys.stdin)
    for a in d['result']['agents']:
        if a.get('name')==alvo: print(a.get('agent_status') or 'unknown'); break
    else: print('ausente')
except Exception: print('unknown')
"
}
todos_status() { # imprime linhas "agente status"
  timeout 25 herdr agent list 2>/dev/null | python3 -c "
import json,sys
alvos=${AGENTES_PY}
try:
    d=json.load(sys.stdin)
    por={a.get('name'):a.get('agent_status') or 'unknown' for a in d['result']['agents']}
    for n in alvos: print(n, por.get(n,'ausente'))
except Exception as e: print('ERRO', e)
"
}
AGENTES_PY="$(python3 -c "import json;print(json.dumps('${AGENTES[*]}'.split()))")"

echo "$(date '+%F %T') coletor armado: run=$RUN agentes=${AGENTES[*]} timeout=${TIMEOUT}s" | tee -a "$LOG"

# ------------------------------------------------------------------ espera
INICIO=$(date +%s)
VIU_TRABALHANDO=$JA_IDLE
while :; do
  AGORA=$(date +%s)
  [ $((AGORA - INICIO)) -ge "$TIMEOUT" ] && {
    echo "$(date '+%F %T') TIMEOUT atingido" | tee -a "$LOG"
    break
  }
  MAPA=$(todos_status)
  echo "$(date '+%F %T') $MAPA" | tr '\n' ';' >>"$LOG"
  echo >>"$LOG"
  # `blocked` NAO e' conclusao: pode ser dialogo de aprovacao OU um falso bloqueio
  # (screen_detection_skip_reason: full_lifecycle_hook_authority faz o wait reportar
  # blocked enquanto o agente trabalha). So idle/done/ausente encerram a rodada.
  ALGUM_ATIVO=$(echo "$MAPA" | grep -cE ' (working|blocked)$' || true)
  [ "$ALGUM_ATIVO" -gt 0 ] && VIU_TRABALHANDO=1
  if [ "$VIU_TRABALHANDO" = "1" ] && [ "$ALGUM_ATIVO" = "0" ]; then
    echo "$(date '+%F %T') todos ociosos: capturando" | tee -a "$LOG"
    break
  fi
  sleep "$INTERVALO"
done

# ---------------------------------------------------------------- captura
for a in "${AGENTES[@]}"; do
  timeout 40 herdr agent read "$a" --source recent-unwrapped --lines 250 >"$OUT/$a.raw.txt" 2>/dev/null || true
  awk '/DONE \| BLOCKED|BLOCKED \| FAILED|NEEDS_INPUT|^ *PASS$|^ *FAIL$/{f=1} f' "$OUT/$a.raw.txt" | head -45 >"$OUT/$a.final.txt"
  [ -s "$OUT/$a.final.txt" ] || tail -30 "$OUT/$a.raw.txt" >"$OUT/$a.final.txt"
done

{
  echo "# Outputs finais — run $RUN"
  echo
  echo "- coletado em: $(date '+%F %T')"
  echo "- coletor: $(basename "$0") (poll ${INTERVALO}s)"
  echo
  echo "## Estado dos agentes"
  echo '```'
  todos_status
  echo '```'
  for a in "${AGENTES[@]}"; do
    echo
    echo "## $a"
    echo '```'
    cat "$OUT/$a.final.txt"
    echo '```'
  done
} >"$OUT/RESUMO.md"

echo "$(date '+%F %T') pronto: $OUT/RESUMO.md" | tee -a "$LOG"
echo "RESUMO: $OUT/RESUMO.md"
exit 0
