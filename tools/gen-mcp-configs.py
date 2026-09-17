#!/usr/bin/env python3
"""Gera os arquivos de configuração MCP de cada CLI a partir de mcp/servers.json.

Fonte única: edite servers.json e rode este script. A saída vai para
mcp/generated/, pronta para copiar (ou mesclar) no arquivo de cada CLI.

    python3 tools/gen-mcp-configs.py            # gera tudo
    python3 tools/gen-mcp-configs.py --list      # só lista os MCPs e o porquê
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "mcp" / "servers.json"
OUT = ROOT / "mcp" / "generated"


def load():
    return json.loads(SRC.read_text(encoding="utf-8"))["servers"]


def claude(servers):
    """~/.claude.json  ou  <projeto>/.mcp.json  ->  {"mcpServers": {...}}"""
    out = {}
    for name, s in servers.items():
        if s.get("transport") == "remote":
            out[name] = {"type": "http", "url": s["url"]}
        else:
            e = {"command": s["command"][0], "args": s["command"][1:]}
            if s.get("env"):
                e["env"] = s["env"]
            out[name] = e
    return {"mcpServers": out}


def codex(servers):
    """~/.codex/config.toml  ->  [mcp_servers.<nome>]"""
    lines = ["# Cole em ~/.codex/config.toml (ou no .codex/config.toml do projeto).", ""]
    for name, s in servers.items():
        lines.append(f"[mcp_servers.{name}]")
        if s.get("transport") == "remote":
            lines.append(f'url = "{s["url"]}"')
        else:
            lines.append(f'command = "{s["command"][0]}"')
            args = ", ".join(json.dumps(a) for a in s["command"][1:])
            lines.append(f"args = [{args}]")
        for k, v in (s.get("env") or {}).items():
            lines.append(f'# env: {k} = "{v}"')
        lines.append("")
    return "\n".join(lines)


def opencode(servers):
    """~/.config/opencode/opencode.json  ->  {"mcp": {nome: {type: local|remote}}}"""
    out = {}
    for name, s in servers.items():
        if s.get("transport") == "remote":
            out[name] = {"type": "remote", "url": s["url"], "enabled": True}
        else:
            e = {"type": "local", "command": s["command"], "enabled": True}
            if s.get("env"):
                e["environment"] = s["env"]
            out[name] = e
    return {"$schema": "https://opencode.ai/config.json", "mcp": out}


def hermes(servers):
    """~/.hermes/config.yaml  ->  mcp_servers:"""
    lines = ["# Cole o bloco mcp_servers: em ~/.hermes/config.yaml.", "mcp_servers:"]
    for name, s in servers.items():
        lines.append(f"  {name}:")
        if s.get("transport") == "remote":
            lines.append(f'    url: "{s["url"]}"')
        else:
            lines.append(f'    command: "{s["command"][0]}"')
            args = ", ".join(json.dumps(a) for a in s["command"][1:])
            lines.append(f"    args: [{args}]")
        if s.get("env"):
            lines.append("    env:")
            for k, v in s["env"].items():
                lines.append(f'      {k}: "{v}"')
    return "\n".join(lines) + "\n"


def prime(servers):
    """Prime Agent: comandos `prime-agent mcp add` (grava em ~/.prime/agent/settings.json)."""
    lines = ["#!/usr/bin/env bash",
             "# Adiciona os MCPs no Prime Agent (ele guarda tudo em ~/.prime/agent/settings.json).",
             "#   ./mcp-add.sh            # roda de verdade",
             "#   ./mcp-add.sh --dry-run  # só mostra",
             "set -u", "DRY=0", '[ "${1:-}" = "--dry-run" ] && DRY=1', ""]
    for name, s in servers.items():
        if s.get("transport") == "remote":
            cmd = f'prime-agent mcp add {name} --url {s["url"]}'
        else:
            envs = " ".join(f"--env {k}={v}" for k, v in (s.get("env") or {}).items())
            cmd = f'prime-agent mcp add {name} {envs} -- { " ".join(s["command"]) }'.replace("  ", " ")
        lines.append(f'echo "+ {name}"')
        lines.append(f'if [ "$DRY" = "1" ]; then echo "  {cmd}"; else {cmd}; fi')
    lines += ["", "echo", 'echo "confira com: prime-agent mcp list"']
    return "\n".join(lines) + "\n"


def main():
    servers = load()
    if "--list" in sys.argv:
        for name, s in servers.items():
            print(f"{name:<22} {s['package'] if 'package' in s else s.get('url','')} "
                  f"v{s.get('version','?')}  — {s['why'][:80]}")
        return
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "claude.mcp.json").write_text(json.dumps(claude(servers), indent=2) + "\n", encoding="utf-8")
    (OUT / "codex.config.toml").write_text(codex(servers), encoding="utf-8")
    (OUT / "opencode.json").write_text(json.dumps(opencode(servers), indent=2) + "\n", encoding="utf-8")
    (OUT / "hermes.config.yaml").write_text(hermes(servers), encoding="utf-8")
    p = OUT / "prime-agent.mcp-add.sh"
    p.write_text(prime(servers), encoding="utf-8")
    p.chmod(0o755)
    # referência: tudo em um JSON só, para o agente ler e adaptar
    (OUT / "servers.flat.json").write_text(json.dumps(servers, indent=2) + "\n", encoding="utf-8")
    print(f"{len(servers)} MCPs -> {OUT}")
    for f in sorted(OUT.iterdir()):
        print("  ", f.name)


if __name__ == "__main__":
    main()
