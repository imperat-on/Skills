#!/usr/bin/env python3
"""pretooluse-compound-bash-guard.py

Evento: PreToolUse | Matcher: Bash
Decompõe comandos compostos (&&, ||, ;, |, $(), crases, newlines) e valida CADA
subcomando contra uma lista de deny-patterns antes de deixar executar.
É o comportamento do liberzon/claude-hooks (smart_approve.py) reescrito de forma
mínima e auditável — resolve o furo clássico "npm test && rm -rf /".

Entrada : JSON de hook no stdin (tool_name, tool_input.command)
Saída   : JSON hookSpecificOutput.permissionDecision=deny, ou exit 0 silencioso.
Uso     : configure em .claude/settings.json com matcher "Bash".
"""
import json
import os
import re
import sys

# Padrões de negação: (regex, motivo). Podem ser estendidos por env
# CLAUDE_EXTRA_DENY="regex1;;regex2" (separados por ;;).
DENY = [
    (r"\brm\s+(-\w*\s+)*-\w*(rf|fr)\w*\b", "rm recursivo forçado"),
    (r"\brm\s+-\w*r\w*\s+(/|~|\$HOME|\*)", "rm recursivo em caminho crítico"),
    (r"\bmkfs(\.\w+)?\b", "formatação de filesystem"),
    (r"\bdd\b[^\n]*\bof=/dev/", "escrita crua em device"),
    (r"\bgit\s+push\b[^\n]*(\s--force(-\w+)?\b|\s-f\b|\s--mirror\b)", "force-push"),
    (r"\bgit\s+push\b[^\n]*\b(main|master|production)\b", "push em branch protegida"),
    (r"\bgit\s+commit\b[^\n]*--no-verify\b", "pular hooks de commit"),
    (r"\bgit\s+reset\s+--hard\b", "descarte irreversível"),
    (r"\bgit\s+clean\b[^\n]*-[a-z]*f[a-z]*d", "limpeza destrutiva"),
    (r"(curl|wget)[^\n|]*\|\s*(sudo\s+)?(ba|z|k)?sh\b", "pipe-to-shell"),
    (r"\b(chmod|chown)\b[^\n]*\s-R\b", "chmod/chown recursivo"),
    (r"\bsudo\b", "escalada de privilégio"),
    (r"\bnpm\s+install\s+-g\b|\bpip\s+install\s+(--user\s+)?[^\n]*(?!-r)", "instalação global"),
    (r"--dangerously-skip-permissions|--bypass-permissions", "bypass de permissões"),
    (r"\b(shutdown|reboot|halt|poweroff)\b", "controle do host"),
    (r":\(\)\s*\{.*\};:", "fork bomb"),
    (r"\btruncate\b[^\n]*\s-s\s*0\b|>\s*/dev/sda", "sobrescrita destrutiva"),
]

extra = os.environ.get("CLAUDE_EXTRA_DENY", "")
if extra:
    for i, pat in enumerate(p for p in extra.split(";;") if p.strip()):
        DENY.append((pat.strip(), "regra extra #%d" % (i + 1)))

# Separadores de comando compostos. Ordem: preserva $()/crases como tokens próprios.
SPLIT = re.compile(r"&&|\|\||;|\||\n|\$\(|\)|`", re.M)


def subcommands(cmd: str):
    """Devolve cada subcomando individual, incluindo o interior de $() e crases."""
    parts = [p.strip() for p in SPLIT.split(cmd)]
    return [p for p in parts if p]


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0  # fail-open: JSON inesperado nunca deve travar o agente

    if data.get("tool_name") not in ("Bash", "PowerShell"):
        return 0

    cmd = (data.get("tool_input") or {}).get("command", "") or ""
    if not cmd.strip():
        return 0

    # Variáveis de ambiente à frente (FOO=bar git push) são ignoradas na avaliação,
    # mas o comando original continua sendo inspecionado — não deixe isso virar bypass.
    stripped = re.sub(r"^\s*(\w+=\S+\s+)+", "", cmd, flags=re.M)

    for sub in subcommands(stripped) + [stripped]:
        for pattern, why in DENY:
            if re.search(pattern, sub, re.IGNORECASE):
                out = {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "deny",
                        "permissionDecisionReason": (
                            "BLOCKED (%s): subcomando perigoso -> %r. "
                            "Reformule usando uma alternativa não destrutiva."
                            % (why, sub[:160])
                        ),
                    }
                }
                print(json.dumps(out, ensure_ascii=False))
                return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
