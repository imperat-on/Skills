# Skills — kit portátil de skills, hooks e MCPs para CLIs de código

Um repositório só com as skills, os hooks e os MCPs que valem a pena, no formato
aberto **Agent Skills** (`SKILL.md`), para instalar em **Claude Code, Codex,
Hermes Agent, OpenCode e Prime Agent** — e em qualquer outra CLI que leia o
padrão. Feito para sobreviver a uma formatação: clona, roda um script, pronto.

- **146 skills** curadas de 11 fontes, todas validadas contra a spec
- **6 hooks** testados (52 casos automatizados passando) numa política única que roda em várias CLIs
- **13 MCPs** com versão conferida no registry em 2026-09-16
- **17 skills de economia de token**, incluindo `ponytail` (lazy senior: reusar em vez de reescrever)
- **`--always-on`**: deixa `ponytail` + `caveman` ativos em toda sessão, em todas as CLIs
- **Nada de segredo no repo** — chaves vêm sempre de variável de ambiente

Comando único (symlinks, tier core):

```bash
git clone https://github.com/imperat-on/Skills ~/Skills && cd ~/Skills && ./install.sh
```

Se preferir deixar a IA da CLI fazer tudo, cole o conteúdo de
[INSTALL-FOR-AGENT.md](INSTALL-FOR-AGENT.md) na sessão dela.

---

## Onde cada CLI lê as skills

Fonte: documentação oficial de cada produto (links em [REPORT.md](REPORT.md) §5).

| CLI | Diretório de skills | Este kit instala em |
|---|---|---|
| Claude Code | `~/.claude/skills/<nome>/SKILL.md` | `~/.claude/skills` |
| Codex CLI | `~/.agents/skills/<nome>/SKILL.md` | `~/.agents/skills` |
| OpenCode | `~/.config/opencode/skills`, `~/.claude/skills`, `~/.agents/skills` | `~/.agents/skills` |
| Prime Agent | `~/.prime/agent/skills`, `~/.agents/skills` | `~/.agents/skills` |
| Hermes Agent | `~/.hermes/skills/<categoria>/<nome>/SKILL.md` | `~/.hermes/skills` |
| Cursor / Crush / Gemini CLI | `~/.cursor/skills`, `~/.config/crush/skills`, `~/.agents/skills` | `--target cursor\|crush\|gemini` |

`~/.agents/skills/` é o diretório que a convenção Agent Skills compartilha entre
Codex, OpenCode, Prime Agent, Cursor, Crush e Gemini CLI — por isso ele é o
destino padrão, e o symlink mantém tudo atualizado depois de um `git pull`.

## Instalação

```bash
./install.sh                 # tier core (35 skills) nas CLIs detectadas, via symlink
./install.sh --tier all      # as 146 skills
./install.sh --copy          # copia em vez de symlinkar (para CLIs sem suporte a symlink)
./install.sh --target prime  # força um destino (agents|claude|hermes|prime|opencode|crush|cursor|gemini)
./install.sh --list          # mostra exatamente o que iria para onde
./install.sh --dry-run       # não escreve nada
./install.sh --force         # sobrescreve nome já existente no destino
./install.sh --uninstall     # remove só o que este script criou
```

O instalador nunca apaga nada: se um nome já existe no destino, ele pula e avisa
(use `--force`). O registro do que foi instalado fica em
`~/.local/state/skills-kit/installed.list`, que é o que o `--uninstall` usa.

**Por que existe tier:** o Codex limita a lista inicial de skills a ~2% da janela
de contexto e encurta descrições quando há muitas. Instalar 140 skills de uma vez
degrada o disparo de todas. O `core` (35) é o conjunto que eu realmente uso; `extra`
entra por demanda (`--tier all`, ou copiando só o que interessar de `skills/`).

## O que tem dentro

| Categoria | Skills | Para quê |
|---|---|---|
| `skills/coding/` | 36 | Teste antes do código, causa raiz antes do patch, review antes do commit, verificação antes de dizer "pronto" |
| `skills/thinking/` | 27 | Destilar intenção, escrever plano executável, especificar, registrar decisão, pesquisar antes de codar |
| `skills/teams/` | 16 | Subagentes com contexto isolado, worktrees paralelos, review por outro agente, handoff |
| `skills/frontend/` | 27 | Design system, acessibilidade, motion, e2e, QA visual, performance React |
| `skills/orchestration/` | 23 | Loop autônomo, gates de avaliação, harness, MCP, custo/modelo, orquestração multi-CLI |
| `skills/efficiency/` | 17 | Menos token por tarefa: reusar código em vez de escrever, saída comprimida, contexto enxuto |

Catálogo completo, com origem, licença e tamanho de cada skill:
[CATALOG.md](CATALOG.md). Metadado legível por máquina: [manifest.json](manifest.json).

## Hooks

Seis scripts com uma política só, escritos no contrato que **Claude Code, Codex,
Cursor e Hermes** aceitam sem adaptação (JSON no stdin, `exit 2` + stderr para
bloquear):

| Script | Evento | O que faz |
|---|---|---|
| `guard-dangerous.py` | pre-tool | Bloqueia `rm -rf /`, `rm -rf ~/...`, `git push --force`, `--no-verify`, `curl \| bash`, `mkfs`, `dd of=/dev/sdX`, `DROP TABLE`, `terraform destroy`, `crontab -r`… |
| `guard-secrets.py` | pre-tool | Bloqueia leitura/escrita de `.env`, `id_rsa`, `*.pem`, `~/.ssh/**`, `credentials.json` e segredo colado na linha de comando |
| `auto-format.sh` | post-tool | Formata o arquivo editado com o formatador do próprio projeto (prettier/biome/ruff/black/gofmt/rustfmt/shfmt/…) |
| `audit-log.sh` | post-tool | Grava cada chamada de ferramenta em JSONL, com redação de token |
| `session-context.sh` | session start | Injeta branch, working tree e últimos commits no começo da sessão |
| `notify-stop.sh` | stop | Aviso no desktop (+ ntfy/webhook se você configurar) |

```bash
./hooks/install-hooks.sh --dry-run    # ver o que faria
./hooks/install-hooks.sh              # instala nas CLIs detectadas (com backup)
bash tools/test-hooks.sh              # 52 casos, sem depender de CLI nenhuma
```

Detalhes, matriz evento×CLI, `fail_closed` e os hooks extras da comunidade:
[hooks/README.md](hooks/README.md).

Os guards são deliberadamente **previsíveis, não espertos**: bloqueiam padrões
conhecidos e deixam passar `rm -rf node_modules` e `rm -rf /tmp/build`. Um guard
que dá falso positivo em trabalho normal é um guard que você desliga em uma
semana.

## Sempre ativo: ponytail + caveman

```bash
./hooks/install-always-on.sh              # todas as CLIs detectadas
./hooks/install-always-on.sh --dry-run    # ver o que faria
./hooks/install-always-on.sh --remove     # tirar
```

Escreve um bloco com marcador no arquivo de instrução permanente de cada CLI — o
que ela lê no começo de toda sessão:

| CLI | Arquivo | Fonte |
|---|---|---|
| Claude Code | `~/.claude/CLAUDE.md` | docs de skills/memória |
| Codex | `~/.codex/AGENTS.md` (ou `AGENTS.override.md`, se existir) | guides/agents-md |
| OpenCode | `~/.config/opencode/AGENTS.md` | docs/rules |
| Prime Agent | `~/.prime/agent/AGENTS.md` | quickstart |
| Hermes | `~/.hermes/SOUL.md` | identity slot #1 |

O texto mora em [`hooks/always-on.md`](hooks/always-on.md) (fonte única, ~950 bytes ≈
240 tokens por sessão). É idempotente, faz backup e o `--remove` desfaz. Efeito:
o agente procura código existente antes de escrever (`ponytail`) e responde
telegráfico (`caveman`) sem você pedir.

## MCPs

13 servidores com versão fixada e verificada, mais o gerador que escreve a
configuração de cada CLI a partir de uma fonte só:

```bash
python3 tools/gen-mcp-configs.py        # regenera mcp/generated/*
python3 tools/gen-mcp-configs.py --list # tabela: servidor, pacote, versão, por quê
```

Sai config pronta para Claude (`.mcp.json`), Codex (`config.toml`), OpenCode
(`opencode.json`), Hermes (`config.yaml`) e Prime Agent
(`prime-agent mcp add`). Leia [mcp/README.md](mcp/README.md) antes: tem armadilha
de nome de pacote (o npm `mcp-server-git` é placeholder de terceiro) e de
permissão de token.

## Verificação

Não confie no README — rode:

```bash
python3 tools/validate-skills.py    # schema da spec: name/dir, description, frontmatter
bash tools/test-hooks.sh            # comportamental: os 52 casos dos hooks
```

Ambos são stdlib-only. Estado atual nesta máquina: **146 skills, 0 erros, 0
avisos; 52/52 casos de hook passando.**

Verificado ao vivo em **duas** CLIs: Hermes Agent e **OpenCode 1.18.31** (skills,
modos sempre ativos, guard bloqueando `rm -rf` e servidor MCP respondendo —
comandos e saídas no [REPORT.md](REPORT.md)).

## Manter e atualizar

```bash
cd ~/Skills && git pull      # symlinks continuam válidos: nada a recopiar
./install.sh --tier all      # quando quiser ampliar o conjunto
./hooks/install-hooks.sh     # quando os scripts de hook mudarem
```

## Origem e licenças

Skills vindas de obra/superpowers (MIT), affaan-m/ECC (MIT),
wshobson/agents (MIT), vercel-labs/agent-skills (MIT), anthropics/skills (Apache-2.0),
bmad-code-org/BMAD-METHOD (MIT), JuliusBrussee/caveman (MIT na parte de skills),
KINGSTAR-OMEGA/claude-token-optimizer (MIT), DietrichGebert/ponytail (MIT),
max-sixty/worktrunk (MIT/Apache-2.0) e 15 skills pessoais. Crédito por skill, licença,
estrelas medidas e o que foi alterado em cada arquivo: [SOURCES.md](SOURCES.md).
O kit em si é MIT.

## Limites declarados

- Não instalei os hooks automaticamente na sua máquina: revise `hooks/scripts/`
  antes — eles bloqueiam comandos de verdade.
- O schema de hooks do **Cursor** é o único não conferido na documentação
  oficial (veio de um kit de referência da comunidade); está marcado como tal.
- Skills pesadas de terceiros (ECC completo, BMAD completo, spec-kit) ficaram
  fora de propósito: metade de um sistema quebra mais do que ajuda. O veredito
  caso a caso está em [REPORT.md](REPORT.md).
- As skills de origem Hermes referenciam ferramentas do Hermes (`terminal`,
  `read_file`…). Em outras CLIs elas funcionam, mas o agente precisa traduzir o
  nome da ferramenta — está anotado no catálogo.
