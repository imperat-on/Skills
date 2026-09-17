#!/usr/bin/env python3
"""Adiciona/remove um servidor MCP no config do OpenCode (JSONC), preservando
comentários e formatação — o OpenCode não tem `mcp add` não-interativo para stdio.

    opencode-mcp-edit.py add <nome> <comando> "<args>" "[ENV=VAL,ENV2=VAL2]"
    opencode-mcp-edit.py remove <nome>
    opencode-mcp-edit.py list

Mexe em ~/.config/opencode/opencode.jsonc (ou opencode.json). Sempre faz backup
ao lado do arquivo e, se o resultado não passar na validação, restaura o backup.
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import shutil
import sys
from datetime import datetime


def config_path() -> pathlib.Path:
    base = pathlib.Path(os.environ.get("XDG_CONFIG_HOME", pathlib.Path.home() / ".config")) / "opencode"
    for name in ("opencode.jsonc", "opencode.json"):
        if (base / name).exists():
            return base / name
    raise SystemExit(f"nao achei opencode.jsonc/json em {base}")


def strip_jsonc(text: str) -> str:
    """Remove // e /* */ respeitando strings — comentário dentro de URL não conta."""
    out, i, n = [], 0, len(text)
    in_str = False
    while i < n:
        c = text[i]
        if in_str:
            out.append(c)
            if c == "\\" and i + 1 < n:
                out.append(text[i + 1])
                i += 2
                continue
            if c == '"':
                in_str = False
            i += 1
            continue
        if c == '"':
            in_str = True
            out.append(c)
            i += 1
            continue
        if c == "/" and i + 1 < n and text[i + 1] == "/":
            while i < n and text[i] != "\n":
                i += 1
            continue
        if c == "/" and i + 1 < n and text[i + 1] == "*":
            i += 2
            while i + 1 < n and not (text[i] == "*" and text[i + 1] == "/"):
                i += 1
            i += 2
            continue
        out.append(c)
        i += 1
    return "".join(out)


def validate(text: str) -> dict:
    clean = re.sub(r",(\s*[}\]])", r"\1", strip_jsonc(text))  # trailing commas
    return json.loads(clean)


def find_object(text: str, key: str) -> tuple[int, int] | None:
    """Devolve (inicio_chave, fim_objeto) do objeto `"key": {...}` ou None."""
    m = re.search(r'"' + re.escape(key) + r'"\s*:\s*\{', text)
    if not m:
        return None
    start = m.end() - 1  # aponta para o '{'
    depth, i, in_str = 0, start, False
    while i < len(text):
        c = text[i]
        if in_str:
            if c == "\\":
                i += 2
                continue
            if c == '"':
                in_str = False
        elif c == '"':
            in_str = True
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return (m.start(), i)
        i += 1
    return None


def entry_json(name: str, command: str, args: list[str], env: dict[str, str]) -> str:
    obj: dict = {"type": "local", "command": [command, *args], "enabled": True}
    if env:
        obj["environment"] = env
    body = json.dumps(obj, ensure_ascii=False, indent=2)
    body = "\n".join("      " + line for line in body.splitlines())  # indentação
    return f'    "{name}": {body.lstrip()}'


def main() -> int:
    if len(sys.argv) < 2:
        return int(bool(sys.stderr.write(__doc__ or "")))
    action = sys.argv[1]
    path = config_path()
    text = path.read_text(encoding="utf-8")

    if action == "list":
        data = validate(text)
        print(json.dumps(list(data.get("mcp", {})), ensure_ascii=False))
        return 0

    if action == "remove":
        name = sys.argv[2]
        region = find_object(text, "mcp")
        if not region:
            print(f"nao existe bloco 'mcp' em {path}")
            return 0
        start, end = region
        block = text[start : end + 1]
        new_block = re.sub(r'\s*"' + re.escape(name) + r'"\s*:\s*\{.*?\n?\s*\},?', "", block, count=1, flags=re.S)
        if new_block == block:
            print(f"servidor '{name}' nao estava configurado")
            return 0
        new_text = text[:start] + new_block + text[end + 1 :]
    elif action == "add":
        name = sys.argv[2]
        command = sys.argv[3]
        args = sys.argv[4].split() if len(sys.argv) > 4 and sys.argv[4] else []
        env: dict[str, str] = {}
        if len(sys.argv) > 5 and sys.argv[5]:
            for pair in sys.argv[5].split(","):
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    env[k.strip()] = v.strip()
        entry = entry_json(name, command, args, env)
        region = find_object(text, "mcp")
        if region:
            start, end = region
            block = text[start : end + 1]
            if re.search(r'"' + re.escape(name) + r'"\s*:', block):
                print(f"servidor '{name}' ja esta configurado")
                return 0
            inner = block[block.index("{") + 1 : block.rindex("}")]
            inner = inner.rstrip()
            if inner.strip():
                inner = inner.rstrip().rstrip(",") + ",\n"
            new_block = block[: block.index("{") + 1] + inner + entry + "\n  }"
            new_text = text[:start] + new_block + text[end + 1 :]
        else:
            close = text.rindex("}")
            head = text[:close].rstrip()
            if not head.endswith("{"):
                head += ","
            new_text = head + "\n  \"mcp\": {\n" + entry + "\n  }\n" + text[close:]
    else:
        raise SystemExit(f"acao desconhecida: {action}")

    try:
        data = validate(new_text)
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(f"ERRO: resultado invalido ({exc}) — nada foi escrito")
    if action == "add":
        assert name in data.get("mcp", {}), "entrada nao aparece no JSON validado"

    backup = path.with_suffix(path.suffix + f".bak-{datetime.now():%Y%m%d%H%M%S}")
    shutil.copy2(path, backup)
    path.write_text(new_text, encoding="utf-8")
    print(f"ok: {action} '{name or ''}' em {path} (backup: {backup.name})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
