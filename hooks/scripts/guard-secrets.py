#!/usr/bin/env python3
"""guard-secrets — impede que o agente leia ou escreva credenciais.

Evento:  pre_tool_call (Hermes) / PreToolUse (Claude Code, Cursor)
Contrato: exit 2 = bloqueia, motivo no stderr.

Cobre três portas de entrada: o caminho do arquivo (Read/Write/Edit), o
conteúdo sendo gravado (chave privada, token) e o comando de shell
(`cat .env`, `gh auth token`). Arquivos-modelo (.env.example, .env.sample,
.env.template, .env.dist) passam de propósito: documentar variável é trabalho
normal e não vaza segredo.

Ajuste as listas abaixo ao seu projeto. Falsos positivos aqui custam caro
(o agente fica sem conseguir trabalhar), então nada de heurística esperta:
só caminhos e formatos conhecidos.
"""
import json
import os
import re
import sys

# ---- política ---------------------------------------------------------------
SECRET_BASENAMES = {
    ".env", ".envrc", ".netrc", ".pgpass", ".npmrc", ".pypirc",
    "id_rsa", "id_ed25519", "id_ecdsa", "id_dsa",
    "credentials.json", "secrets.json", "secrets.yaml", "secrets.yml",
    "hosts.yml",  # ~/.config/gh/hosts.yml
    "config.json",  # só bloqueado sob ~/.docker (ver SECRET_DIRS)
}
TEMPLATE_SUFFIXES = (".example", ".sample", ".template", ".dist", ".md", ".txt")
SECRET_SUFFIXES = (".pem", ".key", ".p12", ".pfx", ".jks", ".keystore", ".ppk", ".asc")
SECRET_DIR_PARTS = (
    "/.ssh/", "/.aws/", "/.gnupg/", "/.docker/", "/.kube/",
    "/.config/gh/", "/.config/gcloud/", "/.config/age/",
)
SECRET_CONTENT = re.compile(
    r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP |ENCRYPTED )?PRIVATE KEY-----"
    r"|AKIA[0-9A-Z]{16}"
    r"|ASIA[0-9A-Z]{16}"
    r"|ghp_[A-Za-z0-9]{30,}|gho_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}"
    r"|sk-(?:ant-|proj-)?[A-Za-z0-9_-]{24,}"
    r"|xox[baprs]-[A-Za-z0-9-]{15,}"
    r"|AIza[0-9A-Za-z_-]{35}"
    r"|ya29\.[0-9A-Za-z_-]{20,}"
    r"|eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}"  # JWT
)
SHELL_SECRET_READERS = r"(?:cat|bat|less|more|head|tail|grep|rg|awk|sed|strings|xxd|od|base64|cp|scp|rsync|curl|nc|tar)"
SHELL_SECRET_FILES = r"(?:\.env(?:\.[a-z]+)?|id_rsa|id_ed25519|\.netrc|\.pgpass|credentials\.json|\.pem|\.pfx|\.p12)"
SHELL_CHECKS = [
    (re.compile(rf"(?:^|[;&|(]|\n)\s*{SHELL_SECRET_READERS}\b[^\n;|]*{SHELL_SECRET_FILES}", re.I),
     "leitura de arquivo de credencial via shell"),
    (re.compile(r"(?:^|[;&|(]|\n)\s*(?:cat|printf|echo|tee)[^\n;|]*>>?\s*[^\s;|]*\.env\b", re.I),
     "escrita em .env via shell"),
    (re.compile(r"\b(?:gh\s+auth\s+token|aws\s+configure\s+get|gcloud\s+auth\s+print-access-token|"
                r"op\s+item\s+get|security\s+find-generic-password|keychain)", re.I),
     "exfiltração de token de CLI"),
    (re.compile(r"(?:^|[;&|(]|\n)\s*(?:cp|scp|rsync|curl|wget|nc|socat)\b[^\n;|]*(?:\.ssh/|\.aws/|\.netrc|\.env\b)", re.I),
     "cópia/envio de credencial para fora"),
    (re.compile(r"\bgit\s+add\b[^\n;|]*(?:\.env\b|\.pem\b|\.key\b|id_rsa)", re.I),
     "git add de arquivo de credencial"),
]


def load_tool() -> tuple[str, dict]:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return "", {}
    if not isinstance(payload, dict):
        return "", {}
    ti = payload.get("tool_input")
    if not isinstance(ti, dict):
        ti = {}
    return str(payload.get("tool_name", "")), ti


def block(reason: str) -> None:
    sys.stderr.write(
        f"BLOQUEADO pelo guard-secrets: {reason}\n"
        "Credencial não entra no contexto do agente — peça ao usuário para ler ou configurar.\n"
    )
    sys.exit(2)


def first(ti: dict, *keys: str) -> str:
    for k in keys:
        v = ti.get(k)
        if isinstance(v, str) and v.strip():
            return v
    return ""


def is_template(path: str) -> bool:
    base = os.path.basename(path)
    return base.endswith(TEMPLATE_SUFFIXES) or base in {"example.env", "env.example"}


def check_path(path: str) -> None:
    if not path or is_template(path):
        return
    base = os.path.basename(path)
    norm = path.replace("\\", "/")
    if base in SECRET_BASENAMES and not base.startswith("config.json"):
        block(f"arquivo de credencial: {base}")
    if base in {".env", ".envrc"} or base.startswith(".env."):
        block(f"arquivo de ambiente: {base}")
    if base.endswith(SECRET_SUFFIXES):
        block(f"material de chave/certificado: {base}")
    for part in SECRET_DIR_PARTS:
        if part in norm:
            block(f"diretório de credenciais do usuário: {part}")


def check_content(content: str) -> None:
    if content and SECRET_CONTENT.search(content):
        block("segredo em texto plano sendo gravado num arquivo")


def check_command(cmd: str, combined: str) -> None:
    if not cmd:
        return
    for pat, reason in SHELL_CHECKS:
        if pat.search(cmd):
            block(reason)
    # token colado direto na linha de comando
    if SECRET_CONTENT.search(cmd):
        block("segredo colado na linha de comando (vaza para o histórico)")


PATCH_FILE_RE = re.compile(r"^\*\*\* (?:Add|Update|Delete|Move) File: (.+)$", re.M)


def check_patch(text: str) -> None:
    """O Codex entrega edits como texto de patch em `command`; extrai os alvos."""
    if "*** Begin Patch" not in text and "*** Add File:" not in text:
        return
    targets = PATCH_FILE_RE.findall(text)
    for t in targets:
        check_path(t.strip())
    check_content(text)
    if not targets and SECRET_CONTENT.search(text):
        block("patch contendo material secreto")


def main() -> None:
    tool, ti = load_tool()
    cmd = first(ti, "command", "cmd")
    path = first(ti, "file_path", "path", "filePath", "target_file", "file")
    body = first(ti, "content", "new_string", "new_str", "text")
    if not (cmd or path or body):
        sys.exit(0)
    check_path(path)
    check_content(body)
    check_command(cmd, f"{cmd} {path}")
    if tool.lower() == "apply_patch" or "*** Begin Patch" in cmd:
        check_patch(cmd)
    sys.exit(0)


if __name__ == "__main__":
    main()
