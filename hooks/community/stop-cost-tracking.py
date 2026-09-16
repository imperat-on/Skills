#!/usr/bin/env python3
"""stop-cost-tracking.py

Evento: Stop | Matcher: (sem matcher)
Lê transcript_path (JSONL da sessão), soma tokens de entrada/saída/cache e estima
custo por modelo. Escreve relatório diário em CSV e, opcionalmente, injeta um
resumo no contexto via hookSpecificOutput.additionalContext do Stop.

Fontes: karanb192/claude-code-hooks (plugins/cache-tax, "Cost tracker hook" citado
        no awesome-claude-code-hooks), disler (stop.py lê transcript).
Env   : CLAUDE_HOOK_LOG_DIR, CLAUDE_COST_USD_PER_MTOK (JSON opcional de preços).

Nunca bloqueia o Stop (exit 0).
"""
import json
import os
import sys
import time
from collections import defaultdict
from pathlib import Path

# Preços em USD por milhão de tokens. Ajuste com CLAUDE_COST_USD_PER_MTOK,
# ex.: '{"input":3.0,"output":15.0,"cache_read":0.3,"cache_write":3.75}'
DEFAULT_PRICES = {"input": 3.0, "output": 15.0, "cache_read": 0.30, "cache_write": 3.75}


def load_prices():
    raw = os.environ.get("CLAUDE_COST_USD_PER_MTOK")
    if not raw:
        return DEFAULT_PRICES
    try:
        return {**DEFAULT_PRICES, **json.loads(raw)}
    except json.JSONDecodeError:
        return DEFAULT_PRICES


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0

    transcript = data.get("transcript_path")
    if not transcript or not os.path.isfile(transcript):
        return 0

    totals = defaultdict(int)
    per_model = defaultdict(lambda: defaultdict(int))

    with open(transcript, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            usage = (rec.get("message") or {}).get("usage") or rec.get("usage")
            if not isinstance(usage, dict):
                continue
            model = (rec.get("message") or {}).get("model") or rec.get("model") or "unknown"
            fields = {
                "input": usage.get("input_tokens", 0) or 0,
                "output": usage.get("output_tokens", 0) or 0,
                "cache_read": usage.get("cache_read_input_tokens", 0) or 0,
                "cache_write": usage.get("cache_creation_input_tokens", 0) or 0,
            }
            for k, v in fields.items():
                totals[k] += v
                per_model[model][k] += v

    # Estimativa usando um único vetor de preços (o transcript real pode ter
    # múltiplos modelos; refine com um mapa modelo->preço se precisar).
    prices = load_prices()
    cost = sum(totals[k] / 1_000_000.0 * prices.get(k, 0.0) for k in totals)

    log_dir = Path(os.environ.get("CLAUDE_HOOK_LOG_DIR", Path.home() / ".claude" / "hook-logs"))
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        day = time.strftime("%Y-%m-%d")
        with open(log_dir / ("cost-%s.csv" % day), "a", encoding="utf-8") as fh:
            fh.write("%s,%s,%d,%d,%d,%d,%.4f\n" % (
                time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                data.get("session_id"),
                totals.get("input", 0),
                totals.get("output", 0),
                totals.get("cache_read", 0),
                totals.get("cache_write", 0),
                cost,
            ))
    except OSError:
        pass

    summary = (
        "Uso desta sessão: input=%d, output=%d, cache_read=%d, cache_write=%d tokens "
        "(custo estimado ~US$ %.4f)." % (
            totals.get("input", 0), totals.get("output", 0),
            totals.get("cache_read", 0), totals.get("cache_write", 0), cost,
        )
    )
    # additionalContext em Stop é feedback não-erro e mantém a conversa viva.
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "Stop",
            "additionalContext": summary,
        }
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
