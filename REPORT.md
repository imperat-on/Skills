# Relatório — como este kit foi montado, e o que ficou de fora

Pesquisa e curadoria feitas em **2026-09-16** nesta máquina (Arch Linux, node 26,
Python 3.14). Tudo que aparece aqui como número foi medido — API do GitHub
autenticada, clones `--depth 1`, `npm view`, leitura da documentação oficial e
teste rodando. Os dossiês brutos das cinco frentes de pesquisa estão em
[`research/`](research/), cada um declarando quantos itens ficaram sem validação.

---

## 1. Método

Cinco frentes de pesquisa em paralelo, cada uma com a mesma regra: **ou o item é
validado com comando e caminho de arquivo real, ou é marcado `NAO_VALIDADO`**.
Nenhuma skill entrou neste kit por parecer boa — todas as 140 existem no
repositório de origem, foram clonadas e passam pelo validador de schema.

| Dossiê | Frente | Itens marcados NAO_VALIDADO |
|---|---|---|
| `research/01-coding-skills.md` | skills de codificação (8 áreas) | 16 |
| `research/02-thinking-and-teams.md` | pensamento + subagentes | 7 |
| `research/03-frontend-orchestration.md` | frontend + orquestração | 4 |
| `research/04-hooks.md` | hooks (schema oficial + 26 scripts) | 9 |
| `research/05-mcp-and-portability.md` | MCPs + portabilidade entre CLIs | 29 |

Depois da pesquisa, cada candidata passou por **três filtros de curadoria**:

1. **Existe e é verificável** — `gh api`, clone, caminho de arquivo conferido.
2. **Licença permite redistribuir** — MIT ou Apache-2.0; sem licença, fora.
3. **Cabe no orçamento de contexto** — o Codex corta descrições quando há muitas
   skills (limite de ~2% da janela), então o kit tem tier `core` (34) e `extra` (106).

## 2. O que eu validei pessoalmente (não veio de relato de terceiro)

Estrelas medidas via `gh api repos/<repo>` em 2026-09-16:

| Repo | Estrelas | Último push | Licença |
|---|---|---|---|
| obra/superpowers | 287.594 | 2026-09-14 | MIT |
| affaan-m/ECC | 260.098 | 2026-09-15 | MIT |
| anthropics/skills | 176.699 | 2026-09-10 | Apache-2.0 |
| openai/codex | 124.729 | 2026-09-16 | — |
| modelcontextprotocol/servers | 90.388 | 2026-09-03 | MIT |
| upstash/context7 | 62.089 | 2026-09-16 | MIT |
| bmad-code-org/BMAD-METHOD | 53.104 | 2026-09-16 | MIT (SPDX diz NOASSERTION, o LICENSE diz MIT) |
| wshobson/agents | 39.729 | 2026-09-14 | MIT |
| microsoft/playwright-mcp | 37.177 | 2026-09-14 | Apache-2.0 |
| github/github-mcp-server | 32.974 | 2026-09-16 | MIT |
| vercel-labs/agent-skills | 31.248 | 2026-08-28 | MIT (só no README) |
| max-sixty/worktrunk | 7.910 | 2026-09-16 | MIT OR Apache-2.0 |
| JuliusBrussee/caveman | **106.123** | 2026-09-16 | MIT só em `skills/` (engine e proxy são BSL-1.1) |
| KINGSTAR-OMEGA/claude-token-optimizer | 121 | 2026-04-12 | MIT |
| charmbracelet/crush | 28.132 | 2026-09-16 | — |
| disler/claude-code-hooks-mastery | 3.921 | 2026-03-04 | — |

Arquivos de origem clonados e inventariados: **1.120 `SKILL.md`** nos cinco repos
(292 canônicas do ECC, 183 do wshobson, 20 do anthropics, 14 do superpowers e as
traduções espelhadas do ECC — que foram descartadas: 518 dos 1.120 eram cópias
em zh-CN/ja-JP/ko/tr/es do mesmo conteúdo).

Infraestrutura testada nesta máquina (depois da segunda passada de curadoria):

```
python3 tools/validate-skills.py   ->  140 skills, 0 erros, 0 avisos
bash tools/test-hooks.sh           ->  PASS: 52   FAIL: 0
python3 tools/gen-mcp-configs.py   ->  13 MCPs, 5 formatos gerados
```

## 3. As decisões de curadoria que mais mudaram o resultado

**a) Um protocolo de hook, quatro CLIs.** O achado que economizou mais trabalho:
Claude Code, Codex, Cursor e Hermes aceitam o mesmo contrato de hook de shell —
JSON no stdin, `exit 2` + stderr para bloquear. O Hermes documenta isso
explicitamente como compatibilidade (`agent/shell_hooks.py`). Em vez de seis hooks
por CLI, escrevi **um conjunto de scripts** e só a *configuração* muda por CLI.
OpenCode e Prime Agent não têm hook de shell (carregam JS/TS), então nesses dois
um adaptador de ~40 linhas chama os mesmos scripts — a política continua num
lugar só.

**b) Testar o hook, não o descrever.** Os primeiros `guard-dangerous.sh` que
escrevi falharam em dois casos reais: bloqueavam `git push --force-with-lease` e
bloqueavam `echo "cuidado com rm -rf /"`. Reescrevi em Python (onde a lógica de
"`rm` em posição de comando" é legível) e passei a exigir **um caso de permissão
para cada caso de bloqueio**. Foi isso, e não a leitura de docs, que fez os
guards ficarem usáveis: falso positivo é o que faz um guard ser desligado.

**c) `~/.agents/skills/` como destino padrão.** Codex, OpenCode, Prime Agent,
Cursor, Crush e Gemini CLI leem esse diretório (documentado em cada doc).
Instalar uma vez ali cobre cinco CLIs; só Claude Code (`~/.claude/skills`) e
Hermes (`~/.hermes/skills`) precisam de destino próprio.

**d) Tier em vez de tudo de uma vez.** Instalar 140 skills degrada o disparo
porque as descrições competem pelo mesmo orçamento de contexto (o Codex declara
o corte). O `core` (32) é o conjunto de uso diário; o resto entra por demanda.

**e) Symlink, não cópia.** `git pull` atualiza as skills em todas as CLIs sem
reinstalar nada. `--copy` existe para quem usa CLI que não segue symlink.

## 4. O que ficou de fora, e por quê

| Candidato | Estrelas | Motivo de exclusão |
|---|---|---|
| `anthropics/skills: doc-coauthoring` | — | Única skill do repositório **sem arquivo de licença**. Não redistribuível sem ambiguidade. |
| ~~`vercel/agent-skills`~~ → `vercel-labs/agent-skills` | 31.248 | **Correção minha**: procurei em `vercel/*` e tomei 404, e quase descartei o item como fantasma. O repositório existe — é `vercel-labs/agent-skills`. Entrou com 5 skills (`vercel-react-best-practices`, `vercel-composition-patterns`, `web-design-guidelines`, `vercel-react-view-transitions`, `writing-guidelines`). Lição: 404 no nome que EU supus não é prova de inexistência. |
| `superset-sh/skills` | **3** | O dossiê 03 reportou 14.307★ para `superset-orchestrate`. O `gh api` diz **3 estrelas** e licença `NOASSERTION`. Estrela inflada no relato — fora. Foi o spot-check que pegou. |
| `github/spec-kit` (spec-driven development) | 137.349 | MIT e excelente, mas tem só **2 `SKILL.md`** (ambos manutenção interna do próprio repo). O valor dele é o fluxo `/specify → /plan → /tasks`, que não é skill — virou recomendação no §6, não dependência. |
| ECC completo (`--target hermes`, 292 skills) | 260.098 | Já é um instalador próprio, com hooks que resolvem o próprio plugin-root por expressões inline de 700 caracteres. Incluí 55 skills curadas dele em vez de meio sistema. |
| BMAD completo | 53.104 | 39 skills acopladas (build, review, sprint, epics). Levei 6 que se provaram autocontidas (conferi: nenhuma referencia outra skill `bmad-*`). |
| `disler/claude-code-hooks-mastery` | 3.921 | Último push em 2026-03-04, seis meses parado; os hooks dele são exemplos de aula, não política. Ficou como fonte de consulta no dossiê 04. |
| Traduções do ECC (zh-CN, ja-JP, ko, tr, es) | — | 518 arquivos com o mesmo conteúdo em outro idioma. Ruído. |
| `mcp-server-git/fetch/time` via npm | — | Os nomes no npm são placeholders `0.0.1-security` de terceiros. Uso a rota Python (`uvx`). Ver `mcp/README.md`. |

## 4b. Economia de token: o que a segunda busca achou

Pedido explícito depois da primeira entrega ("skills de token_saver validadas por
usuários"). Busca dedicada, e o resultado foi mais estreito do que o barulho sugere:
**a maioria dos "cortes de 70-90% de token" é ferramenta, não skill.**

| Achado | Estrelas | O que é | Decisão |
|---|---|---|---|
| `JuliusBrussee/caveman` | 106.123 | Skill (+ proxy próprio). Comprime a **saída** do agente e o **contexto** (CLAUDE.md, todos) e obriga edição em pedaço | **Entrou**: 9 skills, `skills/efficiency/`. MIT conferido no `LICENSING.md` do repo — a parte paga (engine/proxy/rewriter) é BSL-1.1 e ficou fora |
| `KINGSTAR-OMEGA/claude-token-optimizer` | 121 | `antigravity` + `ultimate-protocol`: edição por trecho, proíbe preâmbulo, proíbe despejo de log no chat | **Entrou** (2 skills, tier extra). Menos tração, mas MIT e o conteúdo é disciplina de prompt, não depende de nada |
| `rtk-ai/rtk` | 80.769 | **Ferramenta**, Apache-2.0: proxy em Rust que comprime a saída de comandos dev (60-90%) | Não é skill. Anotado como ferramenta recomendada |
| `mksglu/context-mode` | 23.291 | **Ferramenta**: isola saída de ferramenta (98% de redução) e persiste memória de sessão | Não é skill. As 11 "skills" do repo são manuais do próprio produto |
| `chethanbhatbs/compactor-skill` | 2 | Skill de compressão | Fora: 2 estrelas, zero validação de usuário |
| `cheche089/token-efficiency-skill` | 1 | Skill de eficiência | Fora: sem licença e sem validação |
| `arXiv 2603.29919` (SkillReducer) | — | Paper: mediu que skills publicadas **aumentam** o consumo em vez de reduzir | Virou critério: descrição curta, corpo enxuto (é o que o `validate-skills.py` audita) |

O que ficou **fora** do caveman, de propósito: `caveman-learn`, `caveman-optimize`,
`caveman-setup`, `caveman-manage`, `caveman-discover`, `caveman-evidence-review` —
todas dependem do gateway Caveman Cloud (a parte BSL). `caveman-compress` entrou
como `extra` e está na tabela de dependências: o script dela chama a API da
Anthropic direto e precisa de `ANTHROPIC_API_KEY`.

**Nota que vale mais que as skills:** o ganho maior de token na sua máquina não vem
de skill nenhuma, vem de cortar o que entra em toda chamada — 140 skills indexadas
(≈18 KB de prompt) e 104 ferramentas de MCP carregadas. As skills comprimem a
saída; o índice e os MCPs incham a entrada.

## 5. Portabilidade: o que realmente quebra

O padrão Agent Skills é bem suportado (a vitrine oficial lista ~35 produtos:
Claude Code, Codex, Copilot/VS Code, Cursor, Gemini CLI, Goose, Roo, Amp, Kiro,
Juno/JetBrains, Factory, OpenHands, Letta, mistral-vibe, Pydantic/pi, nanobot…).
O que quebra na prática, medido no clone:

- **Campo de frontmatter** — a spec define `name`, `description`, `license`,
  `compatibility`, `metadata`, `allowed-tools`. Claude Code, Codex, OpenCode e
  Prime Agent reconhecem os cinco primeiros e **ignoram o resto sem avisar**.
  `allowed-tools` é marcado experimental. Todo `name` tem que ser igual ao nome
  da pasta (o validador do kit checa isso nas 140).
- **Nome de ferramenta dentro do texto** — é o problema real. Skills escritas
  para Hermes dizem `terminal`, `read_file`, `patch`; em Claude Code elas são
  `Bash`, `Read`, `Edit`. A instrução continua utilizável, mas o agente precisa
  traduzir. As 15 skills pessoais herdadas de `~/.hermes/skills` estão marcadas
  por isso no `CATALOG.md`.
- **Imports de `~/.claude/skills`** — OpenCode, Crush e Prime Agent leem esse
  diretório por compatibilidade; Cursor lê `~/.claude/skills` e `~/.codex/skills`.
  Instalar em `~/.claude/skills` faz a skill aparecer em quatro CLIs, mas
  instalar em `~/.agents/skills` é mais neutro — foi a escolha do kit.
- **Hooks** — o Cursor é o único com schema não conferido na doc oficial. Está
  marcado no arquivo e no `hooks/README.md`.
- **Skills com `!`backtick`` (injeção dinâmica do Claude Code)** — o corpo de
  algumas skills do superpowers depende de recursos que só o Claude Code tem.
  Funcionam degradadas nas outras; não as removi porque o conteúdo ainda guia o
  agente.

## 6. Recomendações que não viraram arquivo neste kit

Apontadas com número medido, para decidir depois:

- **`github/spec-kit`** (137k★, MIT) — fluxo spec-driven com comandos `/specify`,
  `/plan`, `/tasks`, `/analyze`. Vale instalar por fora se você quiser contratos
  escritos antes de código em projeto grande.
- **superpowers como plugin do Hermes** — `hermes plugins install obra/superpowers --enable`
  (instalação nativa, 14 skills com bootstrap por harness). Este kit leva 13 dessas
  skills como arquivos; a diferença é que o plugin registra hooks próprios.
- **ECC como sistema completo** — o instalador dele (`./install.sh --profile minimal
  --target hermes`) monta hooks, comandos, regras e agentes. É muito mais do que
  skills; se um dia quiser, instale em paralelo e compare.
- **`mcp/community`** — ver `hooks/community/`: 26 hooks da comunidade (ntfy,
  Telegram, cost tracking, TDD guard) que não passaram pelos 52 testes.

## 7. Limites honestos deste relatório

- Não medi desempenho de skill nenhuma (não rodei evals). Curadoria aqui é
  licença + manutenção ativa + conteúdo verificado + aderência ao que foi pedido.
- As contagens de `NAO_VALIDADO` nos dossiês são auto-declaradas pelos relatórios de
  pesquisa. Spot-checkei **todo item que ia virar dependência** e o resultado foi
  misto: peguei `doc-coauthoring` sem licença, peguei `superset-sh/skills` com 3★
  contra 14.307★ relatados, e errei feio ao descartar `vercel-labs/agent-skills` por
  ter procurado na organização errada. Os 65 itens marcados não foram revalidados.
- Três skills do `vercel-labs/agent-skills` publicam `name` diferente do nome da
  pasta, violando a regra da spec (`name` == pasta). O validador do kit pegou; a
  pasta bundlada foi renomeada para casar, sem editar nenhum arquivo.
- A citação "+90,2% com multi-agente, ~15× tokens" que aparece no dossiê 02 vem de
  blog de engenharia da Anthropic. **Não medi** — é número de terceiro, útil como
  ordem de grandeza, não como garantia.
- Estrelas de repositório grande medem atenção, não qualidade. Um repo de 260k★
  pode ter skill ruim: por isso cada skill foi lida antes de entrar — mas com
  olho de curador, não de benchmark.
- Os dossiês em `research/` incluem citações de Reddit/HN recolhidas pelos
  relatórios de pesquisa. Onde a citação era só opinião, o arquivo diz isso; use
  os dossiês como ponta de partida, não como veredito.

---

*Reprodução: `gh api repos/<repo>`, clones `--depth 1`, `python3 tools/validate-skills.py`,
`bash tools/test-hooks.sh`, `python3 tools/gen-mcp-configs.py`. Os dossiês em `research/`
foram escritos por cinco frentes de pesquisa paralelas em 2026-09-16.*
