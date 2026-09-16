# 05 — Servidores MCP para desenvolvimento & Portabilidade entre CLIs

> Pesquisa de 16/set/2026. Host: Linux (Arch, kernel 7.2.6), node **v26.8.2**, npm **12.0.2**, gh **2.101.0**.
> Todo path marcado `[VALIDADO-LOCAL]` foi confirmado com `ls`/`cat` nesta máquina.
> Todo path marcado `[DOCS]` foi confirmado em documentação oficial (baixada em 16/set/2026).
> O que não deu para confirmar aparece como `NAO_VALIDADO` com o que falta.

---

## Método de validação

| Fonte | Como | Resultado |
|---|---|---|
| Registro npm | `npm view <pkg> version` | Versões reais, coluna `npm` |
| PyPI | `curl https://pypi.org/pypi/<pkg>/json` | Versões reais, para `uvx` |
| GitHub | `gh api repos/<owner>/<repo> --jq .stargazers_count` | Coluna `stars` |
| Docs oficiais | `curl <url>.md` (Mintlify/Docusaurus servem markdown puro) | Fatos de config |
| Máquina local | `ls ~/.claude ~/.codex ~/.config/opencode ~/.config/crush ~/.hermes ~/.roo ~/.agents` | Paths reais |

Fatos do host relevante para este estudo:

```
[VALIDADO-LOCAL] ~/.claude/skills/        16 symlinks → ../../.agents/skills/*
[VALIDADO-LOCAL] ~/.claude/hooks/         herdr-agent-state.sh (3069 B, +x)
[VALIDADO-LOCAL] ~/.claude/agents/        NÃO EXISTE
[VALIDADO-LOCAL] ~/.codex/config.toml     553 B ([model_providers.*], [hooks.state])
[VALIDADO-LOCAL] ~/.codex/hooks.json      SessionStart → bash ~/.codex/herdr-agent-state.sh session
[VALIDADO-LOCAL] ~/.codex/AGENTS.md       NÃO EXISTE
[VALIDADO-LOCAL] ~/.config/opencode/      opencode.jsonc, tui.jsonc, agents/shadow.md, plugins/
[VALIDADO-LOCAL] ~/.config/opencode/commands/  NÃO EXISTE
[VALIDADO-LOCAL] ~/.config/crush/skills/  15 symlinks → ../../../.agents/skills/*
[VALIDADO-LOCAL] ~/.config/crush/crushrc  NÃO EXISTE (nem crush.json)
[VALIDADO-LOCAL] ~/.hermes/skills/        dirs por categoria (apple, creative, research, …) + symlink cdesktop
[VALIDADO-LOCAL] ~/.hermes/config.yaml    NÃO tem bloco `hooks:` de topo
[VALIDADO-LOCAL] ~/.agents/skills/        16 skills — a fonte compartilhada real desta máquina
[VALIDADO-LOCAL] ~/.roo/skills/           15 skills (Roo Code instalado)
[VALIDADO-LOCAL] ~/.codeium/windsurf/     existe, vazio
[VALIDADO-LOCAL] ~/.gemini, ~/.cursor, ~/.cline   NÃO EXISTEM
[VALIDADO-LOCAL] CLIs no PATH             claude, codex, opencode, hermes
[VALIDADO-LOCAL] NÃO instalados           crush, gemini, cursor-agent, aider, goose
```

**Descoberta central do host:** esta máquina já usa `~/.agents/skills/` como diretório-fonte e faz *symlink* para dentro de Claude Code, Crush e Roo. É exatamente o padrão que a Parte C formaliza.

---

# Parte A — Servidores MCP úteis para um dev

## A.0 Antes de tudo: quais são os "oficiais" de verdade

O repositório `modelcontextprotocol/servers` (**90.388 stars**) hoje só mantém **7 reference servers**, e o próprio README avisa que são *"referência educacional, não soluções prontas para produção"*:

| Reference server | Caminho no repo | Existe no npm? | Existe no PyPI? |
|---|---|---|---|
| Everything (teste/debug) | `src/everything` | ✅ `@modelcontextprotocol/server-everything` | ❌ |
| Fetch | `src/fetch` | ❌ 404 | ✅ `mcp-server-fetch` |
| Filesystem | `src/filesystem` | ✅ `@modelcontextprotocol/server-filesystem` | ❌ |
| Git | `src/git` | ❌ 404 | ✅ `mcp-server-git` |
| Memory | `src/memory` | ✅ `@modelcontextprotocol/server-memory` | ❌ (o `mcp-server-memory` do PyPI é só um placeholder reservado) |
| Sequential Thinking | `src/sequentialthinking` | ✅ `@modelcontextprotocol/server-sequential-thinking` | ❌ |
| Time | `src/time` | ❌ 404 | ✅ `mcp-server-time` |

**Arquivados** em `modelcontextprotocol/servers-archived` (não usar em setup novo): GitHub, GitLab, PostgreSQL, SQLite, Slack, Google Drive, Google Maps, Brave Search, Puppeteer, Redis, Sentry, Notion, tudo mais. Os pacotes npm `@modelcontextprotocol/server-github@2025.4.8`, `server-postgres@0.6.2`, `server-puppeteer@2025.5.12`, `server-slack@2025.4.25`, `server-redis@2025.4.25` **ainda existem** mas apontam para código arquivado. Regra prática: para GitHub, Slack, Notion, Sentry, Grafana e Atlassian use os servidores **dos próprios fornecedores**, não os do MCP org.

---

## A.1 Servidores oficiais/reference — tabela validada

| # | Servidor | Pacote | Versão | Instalação | Transporte | stars | Risco principal |
|---|---|---|---|---|---|---|---|
| 1 | **Filesystem** | `@modelcontextprotocol/server-filesystem` | `2026.8.31` | `npx -y @modelcontextprotocol/server-filesystem <dir>` | stdio | 90.388¹ | Leitura/escrita/criação em todo caminho permitido; precisa listar dirs explicitamente |
| 2 | **Git** | `mcp-server-git` (PyPI) | `2026.8.18` | `uvx mcp-server-git --repository <path>` | stdio | 90.388¹ | Só operações git, mas `git` executado com seus privilégios no repo |
| 3 | **Memory** | `@modelcontextprotocol/server-memory` | `2026.8.31` | `npx -y @modelcontextprotocol/server-memory` | stdio | 90.388¹ | Grafo de conhecimento persistente em JSON; vira texto que entra no prompt (superfície de injeção) |
| 4 | **Sequential Thinking** | `@modelcontextprotocol/server-sequential-thinking` | `2026.8.31` | `npx -y @modelcontextprotocol/server-sequential-thinking` | stdio | 90.388¹ | Só scaffolding de raciocínio; queima contexto com muitas "thoughts" |
| 5 | **Time** | `mcp-server-time` (PyPI) | `2026.8.18` | `uvx mcp-server-time` | stdio | 90.388¹ | Baixíssimo risco; útil para o modelo não errar fuso |
| 6 | **Fetch** | `mcp-server-fetch` (PyPI) | `2026.8.18` | `uvx mcp-server-fetch` | stdio | 90.388¹ | **Alto**: puxa conteúdo web arbitrário para o contexto → prompt injection |
| 7 | **Everything** (debug) | `@modelcontextprotocol/server-everything` | `2026.8.31` | `npx -y @modelcontextprotocol/server-everything` | stdio | 90.388¹ | É um servidor de teste; só use para validar cliente novo |

¹ `stars` = repositório único `modelcontextprotocol/servers` (93 kB de README → os 7 sevidores não têm stars individuais).

**Config JSON (Claude Code / Cursor / Cline usam o mesmo shape `mcpServers`):**

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/home/zes/projects"]
    },
    "memory": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-memory"]
    },
    "sequential-thinking": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-sequential-thinking"]
    },
    "time": { "command": "uvx", "args": ["mcp-server-time"] },
    "git": { "command": "uvx", "args": ["mcp-server-git", "--repository", "/home/zes/projects/foo"] }
  }
}
```

> `sequentialthinking` no npm é `server-sequential-thinking` (com hífen antes de "thinking"). O nome antigo `@modelcontextprotocol/server-sequentialthinking` **não existe** — `NAO_VALIDADO` (404).

---

## A.2 Servidores de terceiros / fornecedores — tabela validada

| # | Servidor | Pacote validado | Versão | stars | Instalação | Transporte | Env vars | Risco |
|---|---|---|---|---|---|---|---|---|
| 8 | **GitHub oficial** | Docker `ghcr.io/github/github-mcp-server` (não é npm) | rolling | 32.974 | `docker run -i --rm -e GITHUB_PERSONAL_ACCESS_TOKEN ghcr.io/github/github-mcp-server` **ou** remoto | stdio (docker) / http (remoto) | `GITHUB_PERSONAL_ACCESS_TOKEN` (tem precedência sobre OAuth) | PAT com escopos amplos = escrita em repos, PRs, releases. Use `--toolsets`/`--read-only` para cortar |
| 9 | **GitHub remoto (GitHub-hosted)** | endpoint | — | 32.974 | `claude mcp add --transport http github https://api.githubcopilot.com/mcp/` | **http** | `Authorization: Bearer <PAT>` ou OAuth | Mais simples, mas todo o tráfego passa por GitHub; mesmo risco de escopo do PAT |
| 10 | **Context7** (docs de libs atualizadas) | `@upstash/context7-mcp` | `4.1.1` | 62.089 | `npx -y @upstash/context7-mcp` | stdio | `CONTEXT7_API_KEY` (opcional; sem key há rate limit) | Docs de terceiros entram no prompt; custo de rollout de contexto |
| 11 | **Playwright MCP** | `@playwright/mcp` | `0.0.81` | 37.177 | `npx -y @playwright/mcp@latest` | stdio | — | **Alto**: navega e clica em páginas reais (SSRF, ações autenticadas, exfiltração por formulário). Rode em perfil/container isolado |
| 12 | **Chrome DevTools MCP** | `chrome-devtools-mcp` | `1.9.0` | 52.135 | `npx -y chrome-devtools-mcp@latest` | stdio | — | Mesmo risco do Playwright + acesso ao DevTools do browser com seus cookies/sessões |
| 13 | **Sentry** | `@sentry/mcp-server` | `0.39.0` | 854 (repo `getsentry/sentry-mcp`) | `npx -y @sentry/mcp-server` | stdio (+ http em `sentry-mcp-http`) | `SENTRY_ACCESS_TOKEN`, `SENTRY_HOST` (self-hosted) | Traz stack traces e dados de usuário final para o prompt → PII |
| 14 | **Grafana** | binário Go `mcp-grafana` (não existe `@grafana/mcp-grafana`) | rolling | 3.462 | `go install github.com/grafana/mcp-grafana/cmd/mcp-grafana@latest` | stdio | `GRAFANA_URL`, `GRAFANA_SERVICE_ACCOUNT_TOKEN` (o `GRAFANA_API_KEY` está **deprecado**) | Service account token dá leitura de dashboards/metricas/logs; tokens de escrita expõem alteração de alertas |
| 15 | **Notion oficial** | `@notionhq/notion-mcp-server` | `2.5.1` | 4.636 (repo `makenotion/notion-mcp-server`) | `npx -y @notionhq/notion-mcp-server` | stdio | `NOTION_TOKEN` (internal integration token) | Qualquer página compartilhada com a integration fica legível — cuidado com wikis internas |
| 16 | **Todoist oficial** | `@doist/todoist-mcp` | `13.2.7` | 549 | `npx -y @doist/todoist-mcp` (bin: `todoist-mcp`, e `todoist-mcp-http` para HTTP) | stdio + http | `TODOIST_API_TOKEN` | Escrita/exclusão de tarefas; escopo pessoal, não corporativo |
| 17 | **Atlassian (Jira/Confluence)** | remoto oficial `mcp.atlassian.com` + alt. OSS `mcp-atlassian` | endpoint responde `401` em `/v1/sse` e `/v1/mcp` (existe) / repo 5.910 stars | 5.910 (OSS) | Remoto: `npx -y mcp-remote https://mcp.atlassian.com/v1/sse` — OSS: `uvx mcp-atlassian --transport stdio` | sse/http (oficial) · stdio (OSS) | OSS: `JIRA_URL`, `JIRA_USERNAME`, `JIRA_API_TOKEN`, `CONFLUENCE_URL` | O oficial é o mais seguro em auth (OAuth); o OSS guarda API token em texto. Ambos veem issues/confluence internos |
| 18 | **Slack** | `@modelcontextprotocol/server-slack` (**arquivado**) | `2025.4.25` | — | `npx -y @modelcontextprotocol/server-slack` | stdio | `SLACK_BOT_TOKEN`, `SLACK_TEAM_ID` | Arquivado, sem manutenção. Publica mensagem em canais como o bot |
| 19 | **Brave Search** | `@brave/brave-search-mcp-server` (substitui o reference arquivado) | `2.1.3` | — | `npx -y @brave/brave-search-mcp-server` | stdio | `BRAVE_API_KEY` | Resultados web no contexto; custo por query |

**Pacotes npm que NÃO existem (marcados NAO_VALIDADO, `npm view` = 404):**

| Pacote tentado | Status | Alternativa correta |
|---|---|---|
| `@modelcontextprotocol/server-git` | ❌ 404 | `uvx mcp-server-git` (PyPI) |
| `@modelcontextprotocol/server-fetch` | ❌ 404 | `uvx mcp-server-fetch` (PyPI) |
| `@modelcontextprotocol/server-time` | ❌ 404 | `uvx mcp-server-time` (PyPI) |
| `@modelcontextprotocol/server-sqlite` | ❌ 404 | `uvx mcp-server-sqlite` (PyPI, 2025.4.25) |
| `@modelcontextprotocol/server-notion` | ❌ 404 | `@notionhq/notion-mcp-server` |
| `@modelcontextprotocol/server-sentry` | ❌ 404 | `@sentry/mcp-server` |
| `@grafana/mcp-grafana` | ❌ 404 | binário Go `mcp-grafana` |
| `@modelcontextprotocol/server-tavily` | ❌ 404 | (não verificado) |
| `mcp-server-git` / `mcp-server-fetch` no **npm** | ⚠️ existem como `0.0.1-security` (placeholders de segurança da npm, não são o servidor) | use o pacote PyPI de mesmo nome |
| `@github/mcp-server` | ❌ 404 | Docker `ghcr.io/github/github-mcp-server` |
| `github-mcp-server` (npm) | ⚠️ `1.8.7` mas é de `jungchihoon/github-mcp-server` — **não é oficial** | Docker oficial |
| `@stripe/mcp-server`, `@linear/mcp-server`, `apify-mcp-server`, `@modelcontextprotocol/server-memory-server`, `@sentry/mcp-server-metrics`, `mcp-server-time` (npm) | ❌ 404 | não usar |

**SQLite / Postgres:** ambos os reference servers estão **arquivados**. Para banco de dados o caminho mantido hoje é o `googleapis/genai-toolbox` (**16.455 stars**, MCP Toolbox for Databases, binário Go) ou o driver MCP do próprio fornecedor (Supabase: `@supabase/mcp-server-supabase@0.12.0` ✅). O npm `@modelcontextprotocol/server-postgres@0.6.2` ainda instala, mas é código arquivado e `server-sqlite` só existe via PyPI (`uvx mcp-server-sqlite`).

**Inspector (obrigatório para auditar servidor antes de plugar):** `@modelcontextprotocol/inspector@2.7.0` ✅ — bin `mcp-inspector`; `npx -y @modelcontextprotocol/inspector`.
**Proxy para clientes que não falam OAuth:** `mcp-remote@0.14.2` ✅ — `npx -y mcp-remote <url>`.
**Clientes que não falam HTTP remoto:** Cursor/Windsurf/Cline todos suportam `url` hoje, então `mcp-remote` é fallback.

---

## A.3 Config por CLI (mesmo servidor, sintaxe de cada uma)

| CLI | Arquivo | Shape | Exemplo mínimo |
|---|---|---|---|
| Claude Code | `.mcp.json` (projeto) / `~/.claude.json` (user/local) | `{"mcpServers":{...}}` + `type: stdio\|http\|sse\|ws` | `claude mcp add-json filesystem '{"type":"stdio","command":"npx","args":["-y","@modelcontextprotocol/server-filesystem","/home/zes"]}'` |
| Codex CLI | `~/.codex/config.toml` | `[mcp_servers.<id>]` com `command`/`args`/`env` ou `url`/`bearer_token_env_var`/`http_headers` | `[mcp_servers.filesystem]`<br>`command = "npx"`<br>`args = ["-y","@modelcontextprotocol/server-filesystem","/home/zes"]` |
| OpenCode | `~/.config/opencode/opencode.json` (ou `.jsonc`) | `{"mcp":{"<nome>":{"type":"local","command":[...]}}}` ou `{"type":"remote","url":...}` | `{"mcp":{"fs":{"type":"local","command":["npx","-y","@modelcontextprotocol/server-filesystem","/home/zes"]}}}` |
| Crush | `~/.config/crush/crushrc` (Bash) — `crush.json` é legado/deprecado | `mcp add <nome> --command ... --args ...` | `mcp add fs --command npx --args -y --args @modelcontextprotocol/server-filesystem` |
| Hermes Agent | `~/.hermes/config.yaml` (ou `hermes mcp add`) | `mcp_servers:` YAML | `mcp_servers:`<br>`  filesystem:`<br>`    command: "npx"`<br>`    args: ["-y","@modelcontextprotocol/server-filesystem","/home/zes"]` |
| Gemini CLI | `~/.gemini/settings.json` ou extensão `gemini-extension.json` → `mcpServers` | `{"mcpServers":{...}}` | dentro de `gemini-extension.json`: `"mcpServers":{"fs":{"command":"node","args":["${extensionPath}/s.js"]}}` |
| Cursor | `.cursor/mcp.json` (projeto) / `~/.cursor/mcp.json` (global) | `{"mcpServers":{...,"env":{...},"url":...,"headers":...}}` | `{"mcpServers":{"fs":{"command":"npx","args":["-y","@modelcontextprotocol/server-filesystem","${workspaceFolder}"]}}}` |
| Windsurf | `~/.codeium/windsurf/mcp_config.json` | `{"mcpServers":{...}}` — remoto usa **`serverUrl`** (não `url`) | `{"mcpServers":{"fs":{"command":"npx","args":["-y","@modelcontextprotocol/server-filesystem","/home/zes"]}}}` |
| Cline (CLI) | `~/.cline/mcp.json` | `{"mcpServers":{...}}` com `type: "streamableHttp"` p/ remoto | — |
| Cline (extensão VS Code) | `cline_mcp_settings.json` dentro do `globalStorage` da extensão | `{"mcpServers":{...}}` | Caminho absoluto por SO **NAO_VALIDADO** — os docs só dizem "o MCP settings JSON da extensão"; a constante real é `GlobalFileNames.mcpSettings = "cline_mcp_settings.json"` em `apps/vscode/src/core/storage/disk.ts` |
| Roo Code (global) | `mcp_settings.json` (aberto via *Edit Global MCP*) | `{"mcpServers":{...}}` | Caminho absoluto **NAO_VALIDADO** (docs não publicam; vive no `globalStorage` do VS Code) |
| Roo Code (projeto) | `<repo>/.roo/mcp.json` | `{"mcpServers":{...}}` | ✅ validado nos docs |

**Interpolação de variáveis — divergência importante (quebra config portátil):**

| CLI | Variáveis suportadas |
|---|---|
| Claude Code | `${CLAUDE_PROJECT_DIR}`; expande env do shell |
| Cursor | `${env:NAME}`, `${userHome}`, `${workspaceFolder}`, `${workspaceFolderBasename}`, `${pathSeparator}`, `${/}` |
| Windsurf | `${env:VAR}` e `${file:/path}` (lê conteúdo de arquivo — bom para segredos) |
| Roo Code | `${env:VARIABLE_NAME}` em `args` |
| Hermes | env do YAML; subprocesso recebe ambiente **filtrado** (só `PATH, HOME, USER, LANG, LC_ALL, TERM, SHELL, TMPDIR, XDG_*` + o que você declarar em `env`) |
| OpenCode | `environment:` no bloco local / `headers:` no remoto; sem interpolação nativa |
| Codex | `bearer_token_env_var` aponta para uma var de ambiente (não aceita valor inline) |
| Gemini | `${extensionPath}` dentro de extensão |

Um mesmo `mcp.json` **não** roda em todos: Cursor exige `${env:X}`, Windsurf aceita `${env:X}` mas usa `serverUrl` no remoto, Claude Code quer env do shell. A Parte C resolve isso mantendo um arquivo por CLI.

---

# Parte B — Portabilidade real entre CLIs

## B.1 Onde cada CLI lê o quê

### Claude Code `[DOCS]` + `[VALIDADO-LOCAL]`

| Recurso | Caminho | Notas |
|---|---|---|
| Skills (enterprise) | managed policy settings → `skills/` | maior precedência |
| Skills (pessoal) | `~/.claude/skills/<nome>/SKILL.md` | ✅ existe na máquina (16 symlinks) |
| Skills (projeto) | `.claude/skills/<nome>/SKILL.md` | também em subdiretórios (monorepo) → `/apps/web:deploy` |
| Skills (plugin) | `<plugin>/skills/<nome>/SKILL.md` | vira `/plugin-name:skill-name` |
| Skills legados | `.claude/commands/*.md` | continuam funcionando; command name = nome do arquivo |
| Agentes | `~/.claude/agents/*.md` e `.claude/agents/*.md` | ✅ documentado; ⚠️ `~/.claude/agents/` **não existe** nesta máquina → `NAO_VALIDADO` local |
| Hooks | `~/.claude/settings.json`, `.claude/settings.json`, `.claude/settings.local.json`, plugin `hooks/hooks.json`, frontmatter de skill (`hooks:`) | ✅ `~/.claude/hooks/herdr-agent-state.sh` existe e é referenciado |
| MCP | `~/.claude.json` (scope local e user), `.mcp.json` (scope project) | `claude mcp add` grava nesses arquivos |
| Contexto | `CLAUDE.md` / `~/.claude/CLAUDE.md` | |

### OpenAI Codex CLI `[DOCS]` + `[VALIDADO-LOCAL]`

| Recurso | Caminho | Notas |
|---|---|---|
| Config | `~/.codex/config.toml` (ou `$CODEX_HOME`) | ✅ existe (553 B) |
| Config de projeto | `.codex/config.toml` (só em projeto "trusted") | `notify`, `model_provider`, `model_providers`, `otel` são **ignorados** em config de projeto |
| Skills (repo) | `$CWD/.agents/skills`, `$CWD/../.agents/skills`, `$REPO_ROOT/.agents/skills` | Codex sobe do CWD até a raiz do repo |
| Skills (user) | `$HOME/.agents/skills` | ✅ a máquina tem essa pasta |
| Skills (admin/sistema) | `/etc/codex/skills` | |
| **Symlink de skill** | **suportado explicitamente** — "Codex supports symlinked skill folders and follows the symlink target" | 🔑 decisivo para a Parte C |
| Hooks | `~/.codex/hooks.json` **e** `[hooks]` inline em `config.toml`; ligado por `features.hooks` | ✅ `~/.codex/hooks.json` existe com `SessionStart` |
| MCP | `[mcp_servers.<id>]` em `config.toml` | ✅ validado no config-reference |
| Instruções | `~/.codex/AGENTS.md` (global) e `AGENTS.md` por diretório; fallback via `project_doc_fallback_filenames`; `AGENTS.override.md` tem prioridade | ⚠️ `~/.codex/AGENTS.md` **não existe** na máquina |
| Notify | `notify` = array de string (comando recebe JSON) | só em config de usuário |
| Profiles | `$CODEX_HOME/<profile>.config.toml` (`--profile <nome>`) | |

### OpenCode `[DOCS]` + `[VALIDADO-LOCAL]`

| Recurso | Caminho | Notas |
|---|---|---|
| Config global | `~/.config/opencode/opencode.json` (ou `.jsonc`) | ✅ existe `opencode.jsonc` (6352 B) |
| Config projeto | `opencode.json` na raiz | |
| TUI | `~/.config/opencode/tui.json` | ✅ existe `tui.jsonc` |
| Skills | `~/.config/opencode/skills/<n>/SKILL.md`, `.opencode/skills/`, **`~/.claude/skills/`**, **`~/.agents/skills/`**, `.claude/skills/`, `.agents/skills/` | abre o leque de compatibilidade |
| Agentes | `~/.config/opencode/agents/` e `.opencode/agents/` | ✅ existe `agents/shadow.md`; docs aceitam plural `agents/` e singular `agent/` |
| Comandos | `.opencode/commands/` / `commands/`; `~/.config/opencode/` idem | ⚠️ diretório `commands/` **não existe** na máquina |
| Plugins (hooks) | `~/.config/opencode/plugins/*.{js,ts}` e `.opencode/plugins/` | ✅ existe `plugins/herdr-agent-state.js` |
| Instruções | `AGENTS.md` (projeto), `~/.config/opencode/AGENTS.md` (global), fallback `CLAUDE.md` e `~/.claude/CLAUDE.md` | desliga com `OPENCODE_DISABLE_CLAUDE_CODE*` |
| MCP | chave `mcp` no config | |

### Crush (charmbracelet) `[DOCS]` + `[VALIDADO-LOCAL]`

| Recurso | Caminho | Notas |
|---|---|---|
| Config | `~/.config/crush/crushrc` (Bash!) — prioridade `./.crushrc` > `./crushrc` > `~/.config/crush/crushrc` | ⚠️ **não existe** nesta máquina |
| Config JSON legado | `crush.json` (`$CRUSH_GLOBAL_CONFIG`) | deprecado, mas suportado. ⚠️ perigoso: `$(...)` no JSON executa no load |
| Estada/estado | `~/.local/share/crush/crush.json` | só estado, não editar |
| Skills | `$CRUSH_SKILLS_DIR`, `~/.config/agents/skills/`, `~/.config/crush/skills/`, **`~/.agents/skills/`**, **`~/.claude/skills/`** + `options.skills_paths` | ✅ `~/.config/crush/skills/` tem 15 symlinks para `~/.agents/skills/*` |
| Skills (projeto) | `.agents/skills`, `.crush/skills`, `.claude/skills`, `.cursor/skills` | aceita `.cursor/skills` — incomum e útil |
| Contexto | `~/.config/crush/CRUSH.md` + `~/.config/AGENTS.md` (compartilhado com outras CLIs) | `option global-context-path` customiza |
| **Hooks** | `hook add <evento> --command ... [--matcher regex] [--name x] [--timeout s]` no `crushrc` | eventos citados: `PreToolUse` |
| MCP | `mcp add <nome> --type stdio\|sse\|http --command ... --args ... --env k v --url ... --header k v [--oauth true]` | |
| LSP | `lsp add <nome> --command <bin>` | |

### Hermes Agent (Nous Research) `[DOCS]` + `[VALIDADO-LOCAL]`

| Recurso | Caminho | Notas |
|---|---|---|
| Config | `~/.hermes/config.yaml` (`$HERMES_HOME` em perfis) | ✅ existe (7504 B) |
| Segredos | `~/.hermes/.env` — **só credenciais**; setting não vai em `.env` | |
| Skills | `~/.hermes/skills/<categoria>/<nome>/SKILL.md` | ✅ existe com categorias reais (`apple`, `creative`, `research`, `software-development`, …) |
| Skills (projeto) | `<repo>/.hermes/skills/` e `<repo>/.agents/skills/` | mesma convenção cross-tool |
| Skills (externo) | diretórios externos configuráveis (chave `skills.*` no `config.yaml`) apontam para pastas adicionais varridas junto | |
| Perfis | `~/.hermes/profiles/<nome>/` com layout idêntico | |
| Hooks (4 sistemas) | ① Gateway: `~/.hermes/hooks/<nome>/{HOOK.yaml,handler.py}` ② Plugin: `ctx.register_hook()` ③ Shell: bloco `hooks:` no `config.yaml` (scripts em `~/.hermes/agent-hooks/` por convenção) ④ Outbound: `hooks.outbound:` no `config.yaml` | ⚠️ nenhum bloco `hooks:` no `config.yaml` desta máquina |
| Plugins | `~/.hermes/plugins/<nome>/` | ✅ existe `hermes/plugins/herdr-agent-state/` |
| MCP | `mcp_servers:` no `config.yaml` (stdio `command`/`args`/`env`, ou `url`/`headers`) | ferramentas expostas como `mcp_<servidor>_<tool>` |
| Importação | `hermes import-agent [claude-code\|codex]` — importa `CLAUDE.md`/`AGENTS.md`, `permissions.allow/deny`, `mcpServers`/`[mcp_servers.*]`, `skills/`, e mantém em sync com `--sync` | nunca lê `.credentials.json`/`auth.json`, e **remove** env/headers com nome de segredo |
| Contexto de projeto | `AGENTS.md` / `.hermes.md` / `CLAUDE.md` | |

### Gemini CLI `[DOCS]`

| Recurso | Caminho | Notas |
|---|---|---|
| Skills (builtin/extensão/user/workspace) | `~/.gemini/skills/` ou **`~/.agents/skills/`**; `.gemini/skills/` ou **`.agents/skills/`** | dentro de cada tier, `.agents/skills/` ganha do `.gemini/skills/` |
| Extensões | `<home>/.gemini/extensions/<nome>/gemini-extension.json` | pacoteia prompts, MCP, comandos, temas, hooks, sub-agents e skills |
| Hooks | `settings.json` → chave `hooks`; precedência `.gemini/settings.json` > `~/.gemini/settings.json` > `/etc/gemini-cli/settings.json` > extensão | eventos: `SessionStart`, `SessionEnd`, `BeforeAgent`, `AfterAgent`, `BeforeModel`, `AfterModel`, `BeforeToolSelection`, `BeforeTool`, `AfterTool`, `PreCompress`, `Notification` |
| Instruções | `GEMINI.md` (global `~/.gemini/GEMINI.md`, workspace, JIT) | nome configurável → pode virar `AGENTS.md` via `context.fileName` |
| MCP | `mcpServers` em settings/`gemini-extension.json` | ⚠️ `~/.gemini` **não existe** nesta máquina |

### Cursor `[DOCS]` + Windsurf `[DOCS]` + Cline/Roo `[DOCS]`

| CLI | Rules/instruções | Skills | MCP global | MCP projeto |
|---|---|---|---|---|
| **Cursor** | `.cursor/rules/*.md` (doc atual puxa `AGENTS.md` 30×) | `NAO_VALIDADO` — a doc de rules/MCP não descreve pasta de skills própria | `~/.cursor/mcp.json` ✅ confirmado | `.cursor/mcp.json` ✅ confirmado |
| **Windsurf/Devin** | global `~/.codeium/windsurf/memories/global_rules.md` (limite 6.000 ch); workspace `.devin/rules/*.md` (preferido) ou `.windsurf/rules/*.md` (limite 12.000 ch); legado `.windsurfrules`; `AGENTS.md` em qualquer nível | **`~/.codeium/windsurf/skills/<n>/SKILL.md`** e **`.windsurf/skills/<n>/SKILL.md`** ✅ confirmado | `~/.codeium/windsurf/mcp_config.json` ✅ | — (mesmo arquivo; workspace rules vão em `.devin/` ou `.windsurf/`) |
| **Cline** | `NAO_VALIDADO` (docs de contexto não estão em `docs/` do repo) | `NAO_VALIDADO` | CLI: `~/.cline/mcp.json` ✅; extensão: `cline_mcp_settings.json` no `globalStorage` (caminho absoluto NAO_VALIDADO) | — |
| **Roo Code** | modo/específico por `.roo/` | **`~/.roo/skills/<n>/SKILL.md`** e **`<repo>/.roo/skills/<n>/SKILL.md`**, mais **`~/.agents/skills/`** e **`.agents/skills/`** ✅ confirmado | `mcp_settings.json` (global; caminho absoluto NAO_VALIDADO) | `<repo>/.roo/mcp.json` ✅ |

> **Nota de convergência + divergência:** Windsurf e Roo **também** leem `.agents/skills` — ou seja, `.agents/skills` é o único diretório entendido por Codex, OpenCode, Crush, Gemini, Hermes, Roo e Windsurf. **Claude Code é a exceção:** `grep "agents/skills" claude-skills.md` → **0 ocorrências**. Claude Code só lê `.claude/skills/` e `~/.claude/skills/`.

---

## B.2 Frontmatter: o que cada CLI entende e o que ignora

Campos do padrão **Agent Skills** (`agentskills.io/specification`, confirmado): `name` (obrigatório, ≤64 ch, `[a-z0-9-]`, sem hífen no início/fim, sem `--`, **deve bater com o nome do diretório**), `description` (obrigatório, ≤1024 ch), `license`, `compatibility` (≤500 ch), `metadata` (map string→string), `allowed-tools` (string separada por espaço — **experimental**).

| Campo | Agent Skills spec | Claude Code | Codex CLI | OpenCode | Crush | Gemini CLI | Roo Code | Windsurf | Hermes |
|---|---|---|---|---|---|---|---|---|---|
| `name` | obrigatório | ✅ (display name; o comando vem do **diretório**) | ✅ obrigatório | ✅ obrigatório, **deve = diretório** | ✅ | ✅ | ✅ deve = diretório/symlink | ✅ obrigatório | ✅ |
| `description` | obrigatório | ✅ recomendado (default: 1ª linha) | ✅ obrigatório | ✅ obrigatório, 1–1024 ch | ✅ | ✅ | ✅ | ✅ obrigatório | ✅ |
| `license` | ✅ | ✅ aceita, **ignora** conteúdo | ⚠️ não é do formato Codex | ✅ | `NAO_VALIDADO` | `NAO_VALIDADO` | `NAO_VALIDADO` | `NAO_VALIDADO` | `NAO_VALIDADO` |
| `compatibility` | ✅ | ✅ aceita, **ignora** | ⚠️ `NAO_VALIDADO` | ✅ | `NAO_VALIDADO` | `NAO_VALIDADO` | `NAO_VALIDADO` | `NAO_VALIDADO` | `NAO_VALIDADO` |
| `metadata` | ✅ | ✅ aceita, **ignora** (`metadata.hermes` é uso do próprio skill) | ⚠️ não nativo | ✅ map string→string | `NAO_VALIDADO` | `NAO_VALIDADO` | `NAO_VALIDADO` | `NAO_VALIDADO` | ✅ usado por Hermes |
| `allowed-tools` | ✅ experimental | ✅ **honrado** (grant até a próxima mensagem); aceita string, vírgula ou lista YAML | ❌ **ignorado** | ❌ **ignorado** (unknown fields são silenciosamente ignorados) | ❌ ignorado (Crush usa `permissions allow/deny`) | ❌ ignorado (Gemini pede consentimento na ativação) | ❌ ignorado | ❌ ignorado | ❌ ignorado (Hermes tem `approvals`/`command_allowlist` no config) |
| `when_to_use` | ❌ | ✅ extensão só-Claude | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `argument-hint`, `arguments` | ❌ | ✅ só-Claude | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `disable-model-invocation` | ❌ | ✅ só-Claude | ❌ | ❌ | ✅ **suportado** | ❌ | ❌ | ❌ | ❌ |
| `user-invocable` | ❌ | ✅ só-Claude | ❌ | ❌ | ✅ **suportado** | ❌ | ❌ | ❌ | ❌ |
| `disallowed-tools`, `model`, `effort`, `context`, `agent`, `background`, `hooks`, `paths`, `shell` | ❌ | ✅ só-Claude | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `agents/openai.yaml` (`interface`, `policy.allow_implicit_invocation`, `dependencies.tools`) | — | ❌ | ✅ **extensão só-Codex** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |

**Payloads de nome (validator do padrão):** um skill que siga só o spec (6 campos) carrega **sem alteração** em Claude Code, Codex, OpenCode, Crush, Gemini, Roo — e provavelmente Windsurf (só exige `name`+`description`). Ou seja: **escreva para o spec, não para a CLI.**

---

## B.3 O que QUEBRA portabilidade

| # | Quebra | Onde dói | Como evitar |
|---|---|---|---|
| 1 | `allowed-tools` como proteção | Codex/OpenCode/Crush/Gemini/Roo ignoram em silêncio → o skill ganha *menos* restrição do que o autor imaginou | Trate como dica só-Claude; para restrição real use as permissões nativas de cada CLI (`permissions deny`, `approvals.deny`, `tools: {skill: false}`) |
| 2 | `name` diferente do diretório | **OpenCode e Roo falham/erram o match**; o spec exige igualdade | Diretório `<skill-name>/SKILL.md` com `name: <skill-name>` idênticos |
| 3 | `name` com maiúscula/underscore/`--` | Reprova em OpenCode, Gemini, Roo e no spec | Regex `^[a-z0-9]+(-[a-z0-9]+)*$` |
| 4 | Frontmatter que não começa na **linha 1** | Claude Code, se `---` não for a 1ª linha, trata o arquivo todo (inclusive `---`) como conteúdo | Nunca ponha BOM, comentário ou linha vazia antes do `---` |
| 5 | `description` longa + sufixo "Use when…" | Claude trunca o par `description`+`when_to_use` em **1.536 ch**; Codex corta descrições quando o orçamento inicial estoura (máx. 2% do contexto ou 8.000 ch) | Mantenha **os primeiros ~57 caracteres autossuficientes** como gatilho |
| 6 | Muitos skills instalados | Codex pode **omitir** skills da lista inicial e mostrar warning; Claude Code corta descrições | Um skill por trabalho, descrições curtas |
| 7 | `.agents/skills` esperando cobertura total | **Claude Code não lê esse diretório** (0 menções nos docs) | Para Claude, symlink/cópia em `~/.claude/skills/` |
| 8 | Path absoluto dentro do `SKILL.md` | Quebra após formatar a máquina / em outro usuário | Use `${CLAUDE_SKILL_DIR}` (Claude), `${extensionPath}` (Gemini) ou caminhos relativos ao skill; em Hermes o corpo referencia `scripts/` relativo |
| 9 | `${CLAUDE_*}` no corpo | Só Claude substitui; nas outras CLIs o literal aparece no prompt | Isole essas variáveis em skills exclusivos de Claude |
| 10 | `hooks:` no frontmatter do skill | Só Claude Code; nos outros é ignorado e o hook **simplesmente não roda** (silêncio perigoso) | Configure hooks nativos por CLI (ver tabela B.1) |
| 11 | Config MCP "universal" | Sem interpolação comum (`${env:X}` do Cursor ≠ env do Claude ≠ `bearer_token_env_var` do Codex ≠ `serverUrl` do Windsurf) | Um arquivo de MCP por CLI, gerado do mesmo inventário (Parte C) |
| 12 | Segredos em texto no MCP | Windsurf **exige** token hardcoded em alguns casos; Cursor aceita `${env:}`; Hermes filtra o ambiente do subprocesso e **remove** segredos no import | Guarde em `~/.hermes/.env`, `pass`, `op read`, ou nos `${file:...}` do Windsurf |
| 13 | `crush.json` / `crushrc` de fonte não confiável | Ambos são **código executável** (`$(...)` roda no load) | Nunca `source` num `crushrc` da internet; revise antes |
| 14 | Skill de symlink com nome diferente | Roo: o `name` deve bater com o **nome do symlink** | Nomeie o link igual ao skill |
| 15 | Skills arquivados do MCP org | Usa pacote npm congelado e sem manutenção (GitHub, Slack, Postgres, SQLite, Notion, Sentry) | Prefira o servidor do fornecedor |

---

# Parte C — Layout do repo único `Skills`

## C.1 Árvore proposta

```
Skills/                                  # repo git, público
├── README.md                            # "cole isto na IA da sua CLI" (ver C.4)
├── install.sh                           # detecta CLIs e instala (symlink por padrão)
├── uninstall.sh
├── LICENSE
├── skills/
│   ├── software-development/
│   │   ├── code-review/SKILL.md
│   │   ├── debugging/SKILL.md
│   │   ├── test-driven-development/SKILL.md
│   │   └── systematic-debugging/SKILL.md
│   ├── research/       ├── productivity/    ├── media/
│   ├── email/          ├── social-media/    └── note-taking/
│   └── <categoria>/<nome>/
│        ├── SKILL.md            # frontmatter SÓ com os 6 campos do spec
│        ├── references/         # docs carregadas sob demanda
│        ├── scripts/            # executáveis
│        ├── templates/          # opcional
│        └── assets/             # opcional
├── hooks/
│   ├── installer.sh                     # instala hooks por CLI presente
│   ├── claude/  settings-hooks.snippet.json
│   ├── codex/   hooks.json
│   ├── gemini/  settings-hooks.snippet.json
│   ├── crush/   hooks.crushrc
│   ├── opencode/ herdr-agent-state.js   # plugin = hook
│   └── hermes/  herdr-agent-state/{HOOK.yaml,handler.py}
├── mcp/
│   ├── README.md                        # inventário: 1 linha por servidor, transporte, segredo
│   ├── claude/.mcp.json                 # {"mcpServers":{...}}
│   ├── codex/config.toml.snippet        # [mcp_servers.<id>]
│   ├── opencode/opencode.json.snippet   # {"mcp":{...}}
│   ├── crush/mcp.crushrc                # mcp add ...
│   ├── hermes/config.yaml.snippet       # mcp_servers:
│   ├── gemini/settings.json.snippet
│   ├── cursor/mcp.json                  # ~/.cursor/mcp.json
│   ├── windsurf/mcp_config.json         # ~/.codeium/windsurf/mcp_config.json
│   ├── cline/mcp.json                   # ~/.cline/mcp.json
│   └── roo/mcp.json                     # <repo>/.roo/mcp.json
├── agents/
│   ├── claude/<nome>.md                 # ~/.claude/agents/
│   └── opencode/<nome>.md               # ~/.config/opencode/agents/
└── tests/
    └── check-frontmatter.sh             # valida name/description/nome-do-dir em todos os skills
```

**Regras de ouro do repo:**
1. `skills/` usa apenas `name`, `description`, `license`, `compatibility`, `metadata`, `allowed-tools`. Nada de `when_to_use`, `paths`, `argument-hint` — isso vai em um arquivo `*.claude.md` de override, se necessário.
2. Cada `<nome>/` tem `name:` idêntico ao nome do diretório.
3. Só caminhos relativos ao skill (`references/x.md`, `scripts/y.sh`). Zero `/home/zes/...`.
4. Nenhum segredo, nenhum token, nenhum PAT no repo. `mcp/*` referencia variáveis de ambiente; tokens ficam em `~/.hermes/.env`, `pass`, ou 1Password (`op read`).
5. `skills/` é a **única fonte de verdade**. Toda CLI recebe symlink — nunca cópia (salvo Windows sem privilégio de symlink).

## C.2 `install.sh` — detecção + symlink

```bash
#!/usr/bin/env bash
# Skills — instala skills/hooks/MCP nas CLIs presentes. Idempotente.
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODE="${MODE:-symlink}"          # symlink | copy
SKILLS_SRC="$REPO/skills"

log()  { printf '  %s\n' "$*"; }
have() { command -v "$1" >/dev/null 2>&1; }

# Um diretório por CLI que consome SKILL.md; ver tabela B.1.
link_skills() {  # $1 = destino
  local dest="$1"; mkdir -p "$dest"
  while IFS= read -r -d '' skill; do
    local name; name="$(basename "$(dirname "$skill")")"
    local target="$dest/$name"
    rm -rf "$target" 2>/dev/null || true
    if [ "$MODE" = copy ]; then cp -R "$(dirname "$skill")" "$target"
    else ln -sfn "$(dirname "$skill")" "$target"; fi
    log "$target"
  done < <(find "$SKILLS_SRC" -name SKILL.md -print0)
}

echo "== Skills installer (mode=$MODE) =="

# ---- Claude Code ----
if have claude || [ -d "$HOME/.claude" ]; then
  echo "[claude-code] skills -> ~/.claude/skills/"      ; link_skills "$HOME/.claude/skills"
  echo "[claude-code] hooks  -> ~/.claude/settings.json" ; bash "$REPO/hooks/installer.sh" claude || true
fi

# ---- OpenAI Codex CLI ----
if have codex || [ -d "$HOME/.codex" ]; then
  # ~/.agents/skills é lido por Codex, OpenCode, Crush, Gemini, Hermes, Roo e Windsurf.
  echo "[codex] skills -> ~/.agents/skills/ (cross-tool)" ; link_skills "$HOME/.agents/skills"
  echo "[codex] hooks  -> ~/.codex/hooks.json"            ; bash "$REPO/hooks/installer.sh" codex || true
fi

# ---- OpenCode ----
if have opencode || [ -d "$HOME/.config/opencode" ]; then
  echo "[opencode] skills -> ~/.config/opencode/skills/"   ; link_skills "$HOME/.config/opencode/skills"
  echo "[opencode] plugins -> ~/.config/opencode/plugins/" ; mkdir -p "$HOME/.config/opencode/plugins" \
    && cp -f "$REPO"/hooks/opencode/*.js "$HOME/.config/opencode/plugins/" 2>/dev/null || true
fi

# ---- Crush ----
if have crush || [ -d "$HOME/.config/crush" ]; then
  echo "[crush] skills -> ~/.config/crush/skills/" ; link_skills "$HOME/.config/crush/skills"
  mkdir -p "$HOME/.config/crush"
  touch "$HOME/.config/crush/crushrc"
  grep -q "Skills repo" "$HOME/.config/crush/crushrc" || \
    { printf '# Skills repo\n' >> "$HOME/.config/crush/crushrc"
      cat "$REPO/hooks/crush/hooks.crushrc" >> "$HOME/.config/crush/crushrc" 2>/dev/null || true
      cat "$REPO/mcp/crush/mcp.crushrc"     >> "$HOME/.config/crush/crushrc" 2>/dev/null || true; }
fi

# ---- Hermes Agent ----
if have hermes || [ -d "$HOME/.hermes" ]; then
  HH="${HERMES_HOME:-$HOME/.hermes}"
  echo "[hermes] skills -> $HH/skills/<categoria>/"   ; link_skills "$HH/skills"
  echo "[hermes] plugins -> $HH/plugins/"             ; mkdir -p "$HH/plugins" \
    && cp -Rf "$REPO"/hooks/hermes/* "$HH/plugins/" 2>/dev/null || true
fi

# ---- Gemini CLI ----
if have gemini || [ -d "$HOME/.gemini" ]; then
  echo "[gemini] skills -> ~/.gemini/skills/" ; link_skills "$HOME/.gemini/skills"
fi

# ---- Cursor ----
if have cursor-agent || [ -d "$HOME/.cursor" ]; then
  mkdir -p "$HOME/.cursor"
  echo "[cursor] mcp -> ~/.cursor/mcp.json" ; [ -f "$HOME/.cursor/mcp.json" ] || cp "$REPO/mcp/cursor/mcp.json" "$HOME/.cursor/mcp.json"
fi

# ---- Windsurf/Devin ----
if [ -d "$HOME/.codeium/windsurf" ]; then
  echo "[windsurf] skills -> ~/.codeium/windsurf/skills/" ; link_skills "$HOME/.codeium/windsurf/skills"
  echo "[windsurf] mcp    -> ~/.codeium/windsurf/mcp_config.json"
fi

# ---- Cline CLI ----
if [ -d "$HOME/.cline" ]; then
  echo "[cline] mcp -> ~/.cline/mcp.json"
fi

# ---- Roo Code ----
if [ -d "$HOME/.roo" ]; then
  echo "[roo] skills -> ~/.roo/skills/" ; link_skills "$HOME/.roo/skills"
fi

echo "== pronto. 'SKILLS_REPO=$REPO' já instalado. Reinicie cada CLI. =="
```

Uso:

```bash
git clone https://github.com/<voce>/Skills.git ~/Documents/projects/Skills
cd ~/Documents/projects/Skills && ./install.sh
MODE=copy ./install.sh        # Windows sem symlink / WSL / docker
```

## C.3 Comandos de instalação por CLI (o que o `install.sh` faz por dentro)

| CLI | Comando equivalente | Destino final dos skills | Tipo |
|---|---|---|---|
| **Claude Code** | `ln -sfn ~/Documents/projects/Skills/skills/<cat>/<n> ~/.claude/skills/<n>` | `~/.claude/skills/<n>` | symlink obrigatório (não lê `.agents/skills`) |
| **OpenAI Codex** | `ln -sfn … ~/.agents/skills/<n>` (ou `$REPO_ROOT/.agents/skills/`) | `~/.agents/skills/<n>` | **symlink suportado oficialmente** |
| **OpenCode** | `ln -sfn … ~/.config/opencode/skills/<n>` | `~/.config/opencode/skills/<n>` (também acha `~/.claude/skills` e `~/.agents/skills`) | symlink |
| **Crush** | `ln -sfn … ~/.config/crush/skills/<n>` | `~/.config/crush/skills/<n>` | symlink |
| **Hermes** | `ln -sfn … ~/.hermes/skills/<categoria>/<n>`; ou `hermes skills install <url\|openai/skills/k8s>` | `~/.hermes/skills/**` | symlink ou `hermes skills install` |
| **Gemini CLI** | `ln -sfn … ~/.gemini/skills/<n>`; ou `gemini skills install <repo.git> --consent --scope user` | `~/.gemini/skills/<n>` ou `~/.agents/skills/<n>` | symlink ou install nativo |
| **Roo Code** | `ln -sfn … ~/.roo/skills/<n>` | `~/.roo/skills/<n>` (também lê `.agents/skills`) | symlink (nome do link **deve** = `name`) |
| **Windsurf/Devin** | `ln -sfn … ~/.codeium/windsurf/skills/<n>` | `~/.codeium/windsurf/skills/<n>` | symlink `NAO_VALIDADO` (docs só descrevem criação manual; symlink costuma funcionar) |
| **Cursor** | sem pasta de skills própria confirmada → instale em `~/.agents/skills/` | `~/.cursor/rules/*.md` para regras | `NAO_VALIDADO` |

Instalação nativa quando existir (preferível para atualização automática):

```bash
hermes skills install openai/skills/k8s          # GitHub repo/path
hermes skills install https://exemplo.com/SKILL.md --name meu-skill
hermes skills install well-known:https://site/.well-known/skills/x
gemini skills install https://github.com/user/repo.git --consent
gemini skills link ~/Documents/projects/Skills/skills/software-development/code-review
```

## C.4 `README.md` — "cole isto na IA da sua CLI"

> **Prompt de bootstrap, copie e cole no chat da CLI desejada.** Ele detecta onde você está, instala os skills por symlink e configura hooks/MCP.

```text
Clone o repo https://github.com/<voce>/Skills.git em ~/Documents/projects/Skills
(se já existir, faça `git pull`).

Depois rode `~/Documents/projects/Skills/install.sh` e me mostre a saída.
Se o symlink não funcionar (Windows sem Developer Mode), rode com MODE=copy.

Depois disso:
1. Confirme que meus skills aparecem na sua lista (ex.: `/skills` no Claude Code e
   no Gemini CLI, `skills_list` no Hermes, Ctrl+P no Crush).
2. Compare ~/.agents/skills/, ~/.claude/skills/ e ~/.config/crush/skills/ e diga
   quais entradas estão quebradas (symlink morto).
3. Aplique as configs de MCP que fazem sentido para mim, lendo o inventário em
   mcp/README.md, e NÃO grave nenhum segredo em arquivo versionado — use
   variável de ambiente ou o gerenciador de segredos.
4. Rode tests/check-frontmatter.sh e corrija o que falhar.
5. No fim, mostre uma tabela: CLI detectada | skills instalados | hooks | MCP | o que falta.
```

Comandos manuais, por CLI (para o README, seção "instalação por CLI"):

```bash
# Claude Code — MCP + verificação
claude mcp add-json filesystem '{"type":"stdio","command":"npx","args":["-y","@modelcontextprotocol/server-filesystem","/home/zes/projects"]}'
claude mcp list

# OpenAI Codex CLI — MCP vai em ~/.codex/config.toml
printf '\n[mcp_servers.filesystem]\ncommand = "npx"\nargs = ["-y","@modelcontextprotocol/server-filesystem","/home/zes/projects"]\n' >> ~/.codex/config.toml

# OpenCode
cat mcp/opencode/opencode.json.snippet >> ~/.config/opencode/opencode.jsonc

# Crush
cat hooks/crush/hooks.crushrc mcp/crush/mcp.crushrc >> ~/.config/crush/crushrc

# Hermes
cat mcp/hermes/config.yaml.snippet >> ~/.hermes/config.yaml   # ou `hermes mcp add`

# Gemini CLI
python3 - <<'PY'
import json,pathlib
p=pathlib.Path.home()/".gemini/settings.json"; p.parent.mkdir(exist_ok=True)
d=json.loads(p.read_text()) if p.exists() else {}
d.setdefault("mcpServers",{}).update(json.load(open("mcp/gemini/settings.json.snippet"))["mcpServers"])
p.write_text(json.dumps(d,indent=2))
PY

# Cursor / Windsurf / Cline
cp mcp/cursor/mcp.json   ~/.cursor/mcp.json
cp mcp/windsurf/mcp_config.json ~/.codeium/windsurf/mcp_config.json
cp mcp/cline/mcp.json    ~/.cline/mcp.json
```

**Recall pós-formatação (o cenário do Davi):** depois de formatar, o único passo manual é `curl -fsSL https://raw.githubusercontent.com/<voce>/Skills/main/install.sh | bash` (ou clonar e rodar) — o `install.sh` detecta quais CLIs existem e liga só as que estão presentes. Um skill dedicado `skills/software-development/skills-repo-bootstrap/SKILL.md` pode ensinar qualquer IA nova a executar o passo a passo do README.

---

## Apêndice — itens `NAO_VALIDADO` (e exatamente o que falta)

| Item | O que falta |
|---|---|
| `~/.claude/agents/` | Diretório não existe nesta máquina; o path está documentado mas não há arquivo local para inspecionar |
| Caminho absoluto do `mcp_settings.json` global do **Roo Code** | Os docs dizem "aberto via Edit Global MCP" sem publicar o caminho por SO |
| Caminho absoluto do `cline_mcp_settings.json` (extensão VS Code) | Só a constante do código (`GlobalFileNames.mcpSettings`); o diretório é o `globalStorage` do VS Code |
| Skills do **Cursor** | Nem `cursor.com/docs/context/rules` nem `/context/mcp.md` descrevem pasta `SKILL.md` própria |
| Skills/rules do **Cline** | Página de contexto não está no repo (`docs/` do cline não tem doc de skills) |
| Suporte a **symlink** de skills no Windsurf e no Cursor | Docs só descrevem criação manual de diretório |
| Frontmatter `license`/`compatibility`/`metadata` em **Crush, Gemini, Roo, Windsurf, Hermes** | Docs confirmam apenas `name`/`description` (e `user-invocable`/`disable-model-invocation` no Crush); o resto fica sem confirmação explícita |
| `@modelcontextprotocol/server-tavily` | 404 no npm; existe outro nome de servidor Tavily não verificado |
| Data exata do snapshot do `ghcr.io/github/github-mcp-server` | Imagem Docker "rolling"; não há versão semântica publicada |
| Tokens de API de terceiros | Endpoints como `mcp.atlassian.com/v1/sse` e `/v1/mcp` respondem **401** (existem, exigem auth) mas nenhuma chamada autenticada foi feita |

---

## Fontes

- `modelcontextprotocol/servers` README (98 kB) e `servers-archived` — lista de referenciais vs. arquivados
- `github/github-mcp-server` README (113 kB) — Docker, remote, PAT, OAuth
- `code.claude.com/docs/en/{mcp,skills,settings,hooks,sub-agents,plugins}.md`
- `developers.openai.com/codex/{config-reference,skills,guides/agents-md}.md`
- `opencode.ai/docs/{skills,mcp-servers,agents,rules,plugins,config}.md`
- `charmbracelet/crush` README + `docs/config/README.md`
- `google-gemini/gemini-cli` `docs/{hooks/*,cli/skills.md,cli/gemini-md.md,extensions/*}`
- `agentskills.io/specification.md` (padrão Agent Skills)
- `cursor.com/docs/context/{rules,mcp}` · `docs.windsurf.com/windsurf/cascade/{mcp,memories,skills}` · `docs.roocode.com/features/{mcp/using-mcp-in-roo,skills}` · `cline/cline` `docs/mcp/mcp-overview.mdx`
- `hermes-agent.nousresearch.com/docs/{user-guide/features/{skills,hooks,mcp,plugins},user-guide/import-from-other-agents}` + skill local `hermes-agent` (`references/native-mcp.md`)
- Validações locais: `npm view`, `curl pypi.org/pypi/<pkg>/json`, `gh api repos/<r>`, `ls/cat` de configs não sensíveis
