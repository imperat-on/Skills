# MCPs

Doze servidores recomendados, com **versão conferida no registry em 2026-09-16**
(`npm view <pacote> version`). Uma fonte só — `servers.json` — e um gerador que
escreve a configuração de cada CLI:

```bash
python3 tools/gen-mcp-configs.py         # mcp/generated/*
python3 tools/gen-mcp-configs.py --list  # tabela: servidor, pacote, versão, por quê
```

## Os que eu instalaria primeiro

| Servidor | Pacote / versão | Por quê | Risco |
|---|---|---|---|
| `context7` | `@upstash/context7-mcp@4.1.1` (npx) | Doc atual de biblioteca no contexto, em vez de o modelo inventar API | baixo |
| `fetch` | `mcp-server-fetch` (**uvx**) | Dar web ao agente pelo caminho mais barato | baixo |
| `git` | `mcp-server-git` (**uvx**) | Histórico/diff/blame como ferramenta, não como shell | baixo |
| `time` | `mcp-server-time` (**uvx**) | Fuso e hora: o modelo erra isso direto | baixo |
| `memory` | `@modelcontextprotocol/server-memory@2026.8.31` | Memória entre sessões, compartilhada por qualquer CLI | baixo |
| `sequential-thinking` | `@modelcontextprotocol/server-sequential-thinking@2026.8.31` | Rascunho de raciocínio quando a CLI não tem reasoning nativo | baixo |
| `playwright` | `@playwright/mcp@0.0.81` | Navegador real: clicar, screenshot, validar UI | médio |
| `chrome-devtools` | `chrome-devtools-mcp@1.9.0` | DOM, console, network, trace de performance | médio |
| `filesystem` | `@modelcontextprotocol/server-filesystem@2026.8.31` | Acesso a arquivo fora do sandbox | **médio** |
| `sentry` | `@sentry/mcp-server@0.39.0` | Stack trace real em vez de print do humano | médio |
| `github` | remoto `https://api.githubcopilot.com/mcp/` | PR/issue/review estruturado | **alto** |
| `everything` | `@modelcontextprotocol/server-everything@2026.8.31` | Testar se o MCP da sua CLI funciona | nulo |

## Duas armadilhas que custam tempo

1. **Nome de pacote sequestrado no npm.** `mcp-server-git`, `mcp-server-fetch` e
   `mcp-server-time` existem no npm apenas como marcadores
   (`0.0.1-security`), publicados por terceiros. Os servidores de referência
   desses três são **Python**: instale por `uvx`, nunca por `npx -y mcp-server-git`.
   (`@modelcontextprotocol/server-git` e `…/server-sqlite` simplesmente não
   existem no npm — dei E404.)
2. **`npx -y` sem versão pega a última a cada start.** Aqui as versões estão
   fixadas de propósito: um servidor MCP roda com as suas credenciais, então
   atualização automática é superfície de ataque. Para atualizar, mude a versão
   no `servers.json`, regenere, leia o changelog.

## Aplicar em cada CLI

Os arquivos saem prontos em `mcp/generated/`:

| CLI | Arquivo gerado | Onde vai |
|---|---|---|
| Claude Code | `claude.mcp.json` | `<projeto>/.mcp.json` ou `~/.claude.json` |
| Codex CLI | `codex.config.toml` | `[mcp_servers.<nome>]` em `~/.codex/config.toml` |
| OpenCode | `opencode.json` | chave `"mcp": { "<nome>": {type: local\|remote} }` em `~/.config/opencode/opencode.json` |
| Hermes Agent | `hermes.config.yaml` | bloco `mcp_servers:` em `~/.hermes/config.yaml` |
| Prime Agent | `prime-agent.mcp-add.sh` | `prime-agent mcp add …` (grava em `~/.prime/agent/settings.json`) |

No Claude Code dá para evitar editar JSON na mão:

```bash
claude mcp add context7 -- npx -y @upstash/context7-mcp@4.1.1
```

## Regras de convivência

- **Contexto é caro.** Todo servidor MCP injeta o schema das suas ferramentas em
  *toda* chamada. O OpenCode avisa isso na própria doc; o GitHub MCP é o exemplo
  clássico de servidor que sozinho come uma fatia grande da janela. Ligue o que
  você usa, desligue o resto (`enabled: false` no OpenCode, remoção no resto).
- **Token = acesso.** `github` com PAT full-scope é dar as chaves do repositório
  para o agente. Prefira read-only e escopo mínimo; o modo remoto usa OAuth.
- **`filesystem` com o home inteiro é backdoor.** Restrinja a
  `~/Documents/projects` (é o que está no `servers.json` de exemplo).
- **Segredo sempre por variável de ambiente**, nunca escrito no arquivo de
  config versionado. O gerador emite placeholders (`<token>`) de propósito.

## Conferir o que foi verificado

```bash
python3 tools/gen-mcp-configs.py --list   # mostra pacote + versão fixada
npm view @upstash/context7-mcp version    # reconfere contra o registry hoje
```

O dossiê completo da pesquisa (o que é oficial, o que é terceiro, 29 itens
marcados como não validados) está em
[`../research/05-mcp-and-portability.md`](../research/05-mcp-and-portability.md).
