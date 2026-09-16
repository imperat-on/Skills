#!/usr/bin/env python3
"""guard-dangerous — bloqueia comandos destrutivos antes de rodarem.

Evento:  pre_tool_call (Hermes) / PreToolUse (Claude Code, Cursor)
Contrato portátil: lê o JSON do hook no stdin; `exit 2` + motivo no stderr
bloqueia a chamada. Uma linha do tempo de referência: se o comando fosse
executado por um humano distraído, ele perderia trabalho?

Só inspeciona o campo de COMANDO (nunca o conteúdo de arquivos), e exige que
o `rm` esteja em posição de comando (início ou depois de ; && | ), para não
bloquear um `echo "nunca rode rm -rf /"`.
"""
import json
import re
import sys

COMMAND_FIELDS = ("command", "cmd", "script", "shell_command")


def load_command() -> str:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return ""
    if not isinstance(payload, dict):
        return ""
    # O Codex manda o patch de arquivo no campo `command` do tool apply_patch.
    # Isso não é shell: policiar aqui daria falso positivo em qualquer patch que
    # toque um script contendo `rm -rf`.
    if str(payload.get("tool_name", "")).lower() in {"apply_patch", "edit", "write"}:
        return ""
    ti = payload.get("tool_input")
    if not isinstance(ti, dict):
        return ""
    parts = [str(ti[k]) for k in COMMAND_FIELDS if isinstance(ti.get(k), str)]
    return "\n".join(parts)


def block(reason: str) -> None:
    sys.stderr.write(
        f"BLOQUEADO pelo guard-dangerous: {reason}\n"
        "Se for intencional, rode o comando manualmente no terminal fora do agente.\n"
    )
    sys.exit(2)


# posição de comando: início da string, depois de ; & | ou de uma quebra de linha
CMD = r"(?:^|[;&|]|\n)\s*(?:sudo\s+|command\s+|env\s+\w+=\S*\s+)*"

# alvos de `rm -rf` que são sempre recusados
RM_FORBIDDEN = re.compile(r"^(/|/\*|~|~/|~/\*|\$HOME|\$\{HOME\}/?|\*|\.|\./|\./\*|\.\.)$")
# ...e o que é permitido mesmo com caminho absoluto (limpeza de build)
RM_ALLOWED_ABS = ("/tmp/", "/var/tmp/")


def check_rm(cmd: str) -> None:
    """`rm -rf` é o comando que mais destrói trabalho. Avalia o alvo, não o verbo."""
    for m in re.finditer(rf"{CMD}(rm)\s+([^;|&\n]+)", cmd, re.IGNORECASE | re.MULTILINE):
        args = m.group(2).strip()
        flags, targets = [], []
        for tok in args.split():
            if tok.startswith("-"):
                flags.append(tok)
            else:
                targets.append(tok)
        recursive = any("r" in f.lower().lstrip("-") for f in flags) or "--recursive" in flags
        forced = any("f" in f.lower().lstrip("-") for f in flags) or "--force" in flags
        if not (recursive and forced):
            continue
        for t in targets:
            if RM_FORBIDDEN.match(t):
                block(f"rm -rf em {t} (raiz, home, diretório atual ou curinga)")
            if t.startswith("/") and not t.startswith(RM_ALLOWED_ABS):
                block(f"rm -rf recursivo em caminho absoluto fora de /tmp: {t}")
            if t.startswith("~") or t.startswith("$HOME") or t.startswith("${HOME}"):
                block(f"rm -rf recursivo dentro do home: {t}")


CHECKS: list[tuple[str, str]] = [
    # disco / kernel
    (rf"{CMD}(mkfs(\.\w+)?|wipefs|sgdisk|parted)\b", "formatação/particionamento de disco"),
    (r"\bdd\b[^\n]*\bof=/dev/(sd|nvme|hd|vd|mmcblk)", "dd gravando direto em dispositivo de bloco"),
    (r">\s*/dev/(sd|nvme|hd|vd|mmcblk)", "redirecionamento para dispositivo de bloco"),
    (r"\bchmod\s+-R\s+(777|666)\s+/(?:\s|$)", "chmod -R 777 na raiz"),
    (r":\(\)\s*\{.*\}\s*;?\s*:", "fork bomb"),
    (rf"{CMD}shutdown\b|{CMD}reboot\b|{CMD}systemctl\s+(poweroff|reboot|halt)",
     "desligar/reiniciar a máquina"),
    # git
    (r"\bgit\s+push\b[^\n;|]*\s--force(?![-\w])", "git push --force (use --force-with-lease)"),
    (r"\bgit\s+push\b[^\n;|]*\s-f(?:\s|$)", "git push -f (use --force-with-lease)"),
    (r"\bgit\s+commit\b[^\n;|]*\s--no-verify\b", "git commit --no-verify pula os hooks de pre-commit"),
    (r"\bgit\s+commit\b[^\n;|]*\s-n(?:\s|$)", "git commit -n pula os hooks de pre-commit"),
    (r"\bgit\s+clean\b[^\n;|]*\s-\w*[fdx]", "git clean -f/-d/-x apaga arquivos não versionados"),
    (r"\bgit\s+(checkout|restore)\b[^\n;|]*\s(--hard|--\s*\.|\.\s*$)", "descarte de alterações locais"),
    (r"\bgit\s+reset\s+--hard\b", "git reset --hard descarta trabalho não commitado"),
    (r"\bgit\s+branch\s+-D\b", "git branch -D apaga branch sem merge"),
    (r"\bgit\s+push\b[^\n;|]*(origin\s+)?(main|master)\b[^\n;|]*--delete", "delete de branch remota principal"),
    (r"\bgit\s+filter-(branch|repo)\b", "reescrita de histórico sem backup"),
    # execução remota cega
    (r"\b(curl|wget)\b[^\n|;]*\|\s*(sudo\s+)?(ba|z|k|d)?sh\b", "pipe de curl/wget direto para shell"),
    (r"\b(curl|wget)\b[^\n|;]*\|\s*(python3?|node|perl|ruby)\b", "pipe de curl/wget direto para interpretador"),
    # dados
    (r"\b(drop|truncate)\s+(table|database|schema)\b", "DROP/TRUNCATE sem revisão"),
    (r"\bDELETE\s+FROM\s+\w+\s*;?\s*$", "DELETE sem WHERE"),
    (r"\bflushall\b|\bFLUSHDB\b", "FLUSHALL/FLUSHDB apaga o banco Redis"),
    # infra
    (r"\bkubectl\s+delete\s+(ns|namespace|deploy|deployment|pvc|pv|statefulset|svc)\b",
     "kubectl delete de recurso de produção"),
    (r"\bterraform\s+(destroy|apply\s+-auto-approve)", "terraform destroy / apply -auto-approve"),
    (r"\b(aws|gcloud|az)\s+.*\b(delete|terminate|rm)\b[^\n]*--force\b", "delete de recurso cloud com --force"),
    (r"\bdocker\s+(system|volume|image)\s+prune\s+-a", "docker prune -a remove imagens/volumes em uso"),
    (r"\bdocker\s+rm\s+-f\b|\bdocker\s+rmi\s+-f\b", "docker rm/rmi -f"),
    # segredos e permissões
    (r"\bpasswd\b\s|>\s*/etc/(passwd|shadow|sudoers)", "alteração de credencial do sistema"),
    (r"\bcrontab\s+-r\b", "crontab -r apaga todos os agendamentos"),
    (r"\bhistory\s+-c\b", "history -c apaga rastro da sessão"),
]


def main() -> None:
    cmd = load_command()
    if not cmd.strip():
        sys.exit(0)
    check_rm(cmd)
    for pattern, reason in CHECKS:
        try:
            if re.search(pattern, cmd, re.IGNORECASE | re.MULTILINE):
                block(reason)
        except re.error as exc:  # padrão quebrado nunca deve bloquear o usuário
            sys.stderr.write(f"guard-dangerous: padrao invalido {pattern!r}: {exc}\n")
    sys.exit(0)


if __name__ == "__main__":
    main()
