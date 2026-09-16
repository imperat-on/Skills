# 03 — Melhores Skills de FRONTEND e ORQUESTRAÇÃO de Agentes para CLIs de IA

**Data:** 2026-09-16 · **Autor:** subagente de pesquisa (Hermes) · **Alvo:** Davi (dev solo, apps desktop/Electron + games, frontend React/Tailwind)

## Metodologia e nível de confiança

Tudo abaixo foi validado com dados reais, não com memória:

```bash
# 1) estrelas + última atividade real (API autenticada)
gh api repos/<org>/<repo> --jq '[.stargazers_count,.pushed_at,.description]'
# 2) estrutura real de arquivos (nunca inventada)
git clone --depth 1 https://github.com/<org>/<repo> /tmp/research/clone/<org>_<repo>
find /tmp/research/clone/<repo> -name SKILL.md
# 3) links de posts verificados por HTTP
curl -s -o /dev/null -w "%{http_code}" -L <url>     # todos os links citados: 200
```

**Legenda de status:** `VM` = validado por API e clone (arquivos listados de verdade) · `VA` = validado só por API (sem clone) · `NAO_VALIDADO` = não consegui confirmar (marcado explicitamente, não use como certo).

Candidatos que **não existem** (404 na API — não invente caminhos a partir deles): `sourcegraph/amp`, `openai/codex-cli` (o repo certo é `openai/codex`), `sanity-io/agent-skills`, `vercel-labs/design-best-practices`, `shadcn/skills`, `mattpocock/skills` (existe, 263.548★, mas sem skills de frontend relevantes no índice pesquisado), repo oficial do `dmux` (só o site dmux.ai responde 200).

---

# SEÇÃO 1 — TOP 10 SKILLS DE FRONTEND

### 1. `frontend-design` (Anthropic oficial) — VM · 176.699★
- **URL:** https://github.com/anthropics/skills
- **Arquivo:** `skills/frontend-design/SKILL.md`
- **Por que:** skill canônica de direção visual — força escolhas de paleta/tipografia/layout específicas do brief em vez do "default de IA"; frontmatter real: *"Guidance for distinctive, intentional visual design… makes choices that don't read as templated defaults"*.
- **Post:** HN 816pts "Claude Skills" (https://news.ycombinator.com/item?id=45607117) e HN 738pts "Claude Skills are awesome, maybe a bigger deal than MCP" (https://news.ycombinator.com/item?id=45619537).

### 2. `web-artifacts-builder` (Anthropic) — VM
- **URL:** https://github.com/anthropics/skills
- **Arquivo:** `skills/web-artifacts-builder/SKILL.md` (+ `scripts/init-artifact.sh`, `scripts/bundle-artifact.sh`)
- **Por que:** a única skill oficial que entrega stack **React 18 + TypeScript + Vite + Tailwind + shadcn/ui** já montada e bundlada em um HTML — é o "artifacts-builder" que o brief pediu (nome real difere: `web-artifacts-builder`).
- **Bônus no mesmo repo:** `skills/canvas-design/SKILL.md`, `skills/theme-factory/SKILL.md`, `skills/brand-guidelines/SKILL.md`, `skills/webapp-testing/SKILL.md`.

### 3. Vercel Agent Skills (oficiais) — VM · 31.248★
- **URL:** https://github.com/vercel-labs/agent-skills · **Docs:** https://vercel.com/docs/agent-resources/skills
- **Arquivos (9 SKILL.md validados):** `skills/react-best-practices/SKILL.md` (React/Next perf — "React and Next.js performance optimization guidelines from Vercel Engineering"), `skills/composition-patterns/SKILL.md` (compound components, sem forwardRef em React 19), `skills/web-design-guidelines/SKILL.md` (audit de UI/a11y — "review my UI", "check accessibility"), `skills/react-view-transitions/SKILL.md`, `skills/react-native-skills/SKILL.md`, `skills/vercel-optimize/SKILL.md`, `skills/deploy-to-vercel/SKILL.md`
- **Por que:** as regras são atômicas e auditáveis (`skills/react-best-practices/rules/async-parallel.md`, `bundle-barrel-imports.md`, `js-index-maps.md`, …) — melhor que prompt genérico para Next.js/Vercel.

### 4. Plugin `ui-design` do wshobson/agents — VM · 39.728★
- **URL:** https://github.com/wshobson/agents
- **Arquivos (9 skills):** `plugins/ui-design/skills/design-system-patterns/SKILL.md`, `visual-design-foundations/SKILL.md` (+ refs `color-systems.md`, `typography-systems.md`, `spacing-iconography.md`), `responsive-design/SKILL.md` (+ `container-queries.md`, `fluid-layouts.md`, `breakpoint-strategies.md`), `interaction-design/SKILL.md`, `web-component-design/SKILL.md` (+ `accessibility-patterns.md`), `react-native-design/SKILL.md`
- **Por que:** é o pacote mais completo de design system como *skill* (tokens, theming, container queries) — 92 plugins no total, multi-harness (Claude Code, Codex, Cursor, OpenCode, Copilot).

### 5. `nextjs-app-router-patterns` + `tailwind-design-system` + `wcag-audit-patterns` (wshobson) — VM
- **URL:** https://github.com/wshobson/agents
- **Arquivos:** `plugins/frontend-mobile-development/skills/nextjs-app-router-patterns/SKILL.md` (Next 14+ App Router, RSC, streaming, parallel routes), `plugins/frontend-mobile-development/skills/tailwind-design-system/SKILL.md`, `plugins/frontend-mobile-development/skills/react-state-management/SKILL.md`, `plugins/accessibility-compliance/skills/wcag-audit-patterns/SKILL.md`, `plugins/accessibility-compliance/skills/screen-reader-testing/SKILL.md`
- **Por que:** cobre Next App Router + Tailwind v4 + WCAG num único plugin marketplace — exatamente o stack React/Tailwind priorizado.

### 6. Subagentes de UI (`ui-designer`, `frontend-developer`, `a11y`) — VM · 25.126★
- **URL:** https://github.com/VoltAgent/awesome-claude-code-subagents
- **Arquivos:** `categories/01-core-development/ui-designer.md`, `categories/01-core-development/frontend-developer.md`, `categories/01-core-development/design-bridge.md`, `categories/02-language-specialists/react-specialist.md`, `categories/04-quality-security/ui-ux-tester.md`, `categories/04-quality-security/accessibility-tester.md`
- **Por que:** o "ui-designer" do brief existe literalmente aqui como subagente com system prompt próprio — útil para design-review em subagente separado do que escreveu o código.

### 7. `playwright-skill` (skill) + `microsoft/playwright-mcp` (MCP) — VM · 3.120★ / 37.177★
- **URLs:** https://github.com/lackeyjb/playwright-skill · https://github.com/microsoft/playwright-mcp
- **Arquivos:** `skills/playwright-skill/SKILL.md`, `skills/playwright-skill/API_REFERENCE.md`, `skills/playwright-skill/run.js`, `skills/playwright-skill/lib/helpers.js` (repo tem `.claude-plugin/plugin.json`)
- **Por que:** o MCP oficial dá browser ao agente; a *skill* consome muito menos contexto (foi o argumento que rendeu 189pts no HN: https://news.ycombinator.com/item?id=45642911) — regressão visual/E2E sem inflar a janela.
- **QA extra:** `PramodDutta/qaskills` (225★), `petrkindlmann/qa-skills` (128★, 50 skills de QA).

### 8. `Figma-Context-MCP` + `figma/code-connect` — VM / VA · 15.870★ / 1.573★
- **URLs:** https://github.com/GLips/Figma-Context-MCP · https://github.com/figma/code-connect
- **Arquivos:** `src/mcp-server.ts`, `src/server.ts`, `src/extractors/`, `src/services/`
- **Por que:** entrega layout/estilos do Figma em formato que o agente lê (o mais popular de todos os MCPs de Figma), e o code-connect amarra componente de código ↔ componente de design system.
- **Contexto:** HN 38pts "Figma's MCP Update Reflects a Larger Industry Shift" — https://news.ycombinator.com/item?id=47564159.

### 9. Core Web Vitals / performance: `lighthouse-ci` + `web-vitals` + `lighthouse-mcp-server` — VA · 7.083★ / 8.611★ / 71★
- **URLs:** https://github.com/GoogleChrome/lighthouse-ci · https://github.com/GoogleChrome/web-vitals · https://github.com/danielsogl/lighthouse-mcp-server (base: https://github.com/GoogleChrome/lighthouse, 30.775★)
- **Por que:** fecha o loop de "Core Web Vitals" — o MCP deixa o agente rodar o audit e o lighthouse-ci impede regressão de orçamento de perf a cada commit.
- **NAO_VALIDADO:** não existe skill oficial "core-web-vitals" (busca em `gh api search/repositories` sem resultado relevante); a fonte real da métrica é `web-vitals`.

### 10. Design system pronto + visual regression: `better-design` / `oh-my-design` / `styleseed` + `reg-suit`/`lost-pixel`/`argos` — VM/VA · 235★ / 507★ / 955★ / 1.294★ / 1.684★ / 626★
- **URLs:** https://github.com/marvkr/better-design (MCP + registry com 28 sistemas shadcn validados: `registry/stripe`, `vercel`, `notion`, `supabase`…) · https://github.com/kwakseongjae/oh-my-design (507★, instala 400+ DESIGN.md) · https://github.com/bitjaru/styleseed (955★, 23 skills de método de design) · https://github.com/reg-viz/reg-suit · https://github.com/lost-pixel/lost-pixel · https://github.com/argos-ci/argos
- **Por que:** resolve o problema real de UI gerada por IA (aparência "templated") ancorando o agente em um design system existente, e o VRT pega a regressão visual que teste unitário não pega.

### Menções honrosas (frontend)
| Item | URL | ★ | Nota |
|---|---|---|---|
| Visual regression (bônus) | https://github.com/GoogleChrome/lighthouse / `dequelabs/axe-core` | 30.775 / 7.515 | axe-core = engine de a11y padrão da indústria (VA) |
| Animação | https://github.com/motiondivision/motion · https://github.com/magicuidesign/magicui | 33.618 / 22.307 | Motion (ex-Framer Motion) + MagicUI = componentes animados copiáveis |
| Componentes acessíveis | https://github.com/radix-ui/primitives · https://github.com/tailwindlabs/headlessui · https://github.com/shadcn-ui/ui | 19.280 / 28.742 / 123.990 | base real do shadcn; Tailwind 97.579★ |
| Workshop de componentes | https://github.com/storybookjs/storybook | 91.076 | docs + teste de componente isolado (VA) |
| Índice curado | https://github.com/wilwaldon/Claude-Code-Frontend-Design-Toolkit | 1.115 | "tudo que faz o Claude Code gerar frontends melhores" (VA) |
| Evidência sci-fi→dado | https://github.com/dani-z/frontend-design-skill-benchmark | 24 | benchmark: skill frontend-design **100% vs 28%** de pass rate vs baseline (VA) |
| Anti-slop / motion skills | `dembrandt/dembrandt-skills` (54★) · `joe-watkins/wcag-mcp` (13★) | — | UX/design-system sênior empacotado; WCAG como MCP |
| Godot (contexto games) | https://github.com/htdt/godogen | 6.925 | 337pts no HN: skills que constroem jogos Godot completos |

---

# SEÇÃO 2 — TOP 10 FERRAMENTAS/PADRÕES DE ORQUESTRAÇÃO

### 1. Claude Code: subagents + skills + hooks, e o Agent SDK — VA/VM · 145.410★ (+ SDK Python 8.110★)
- **URLs:** https://github.com/anthropics/claude-code · https://github.com/anthropics/claude-agent-sdk-python · https://github.com/anthropics/claude-agent-sdk-typescript
- **Arquivos:** o próprio repo do SDK expõe `.claude/skills/`, `.claude/commands/`, `.claude/agents/` — confirmados no clone; `examples/` e `e2e-tests/` mostram plugins e session stores.
- **Por que:** é o substrato que os outros orquestradores embrulham — sem entender subagent/`model:`/hook você não controla custo nem paralelismo; o SDK deixa dirigir isso por código.
- **Post:** HN 288pts "How to use Claude Code subagents to parallelize development" — https://zachwills.net/how-to-use-claude-code-subagents-to-parallelize-development/ (discussão: https://news.ycombinator.com/item?id=45181577). Crítica: hooks mal usados dão falso senso de segurança (HN 39pts, https://news.ycombinator.com/item?id=49299985).

### 2. `obra/superpowers` — metodologia de orquestração em skills — VM · 287.594★
- **URL:** https://github.com/obra/superpowers
- **Arquivos (14 SKILL.md validados):** `skills/dispatching-parallel-agents/SKILL.md` (*"Dispatch one agent per independent problem domain. Let them work concurrently"*), `skills/subagent-driven-development/SKILL.md`, `skills/using-git-worktrees/SKILL.md` (*"Detect existing isolation first. Then use native tools. Then fall back to git. Never fight the harness"*), `skills/writing-plans/SKILL.md`, `skills/executing-plans/SKILL.md`, `skills/requesting-code-review/SKILL.md`, `skills/receiving-code-review/SKILL.md`, `skills/verification-before-completion/SKILL.md`, `skills/finishing-a-development-branch/SKILL.md`
- **Por que:** o único conjunto que cobre o ciclo inteiro do dev solo — paralelizar, isolar, revisar cruzado, finalizar branch — em vez de só "rodar N agentes".

### 3. Git worktrees + tmux (padrão manual, pragmático) — VM · worktrunk 7.910★, tmux 49.297★, claude-squad 8.488★
- **URLs:** https://github.com/max-sixty/worktrunk · https://github.com/tmux/tmux · https://github.com/smtg-ai/claude-squad
- **Arquivos:** worktrunk traz **skills próprias**: `skills/worktrunk/SKILL.md` + `skills/worktrunk/reference/claude-code.md`, `switch.md`, `merge.md`, `llm-commits.md`, `hook.md`; e `hooks/hooks.json`. claude-squad implementa em Go: `session/tmux/`, `session/git/`, `daemon/`, `ui/`.
- **Por que:** `git worktree add` + uma pane tmux por agente é o setup com melhor relação esforço/benefício hoje — sem servidor, sem lock-in; worktrunk adiciona o ciclo de vida (create/switch/merge/remove) e hooks por worktree.
- **Posts:** guia prático tmux https://www.dariuszparys.com/claude-code-multi-agent-tmux-setup · Reddit: https://www.reddit.com/r/ClaudeAI/comments/1tp19x7/running_multiple_claude_code_sessions_in_parallel/ · https://www.reddit.com/r/ClaudeAI/comments/1sqxpkv/how_to_use_git_worktrees_with_claude_code/ · https://www.reddit.com/r/ClaudeCode/comments/1srnv9l/layered_parallel_worktrees_with_claude_code_how_i/ · HN 24pts Superset (https://news.ycombinator.com/item?id=46109015). **NAO_VALIDADO:** repo do `dmux` (só https://dmux.ai responde 200).

### 4. Superset — CLI/MCP de coordenação multi-agente — VM · 14.307★ (+ skills 3★)
- **URLs:** https://github.com/superset-sh/superset · https://github.com/superset-sh/skills
- **Arquivos:** `skills/superset-orchestrate/SKILL.md` (protocolo coordenador→workers: criar workspace isolado, lançar worker, mandar follow-up, ler output, rastrear dependências), `skills/superset-10x/SKILL.md`, `skills/superset-mcp/SKILL.md`, `skills/superset-standup/SKILL.md`, `skills/superset-doctor/SKILL.md`
- **Por que:** transforma "N terminais abertos" em protocolo com workspace/agente/terminal e resultado estruturado — e já vem com skill para o próprio agente coordenar, o que é raro.
- **Post:** HN "Run 10 parallel coding agents on your machine" — https://news.ycombinator.com/item?id=46109015

### 5. Fila de tarefas / kanban de agentes — VM/VA · vibe-kanban 28.105★, beads 27.216★, task-master 28.078★
- **URLs:** https://github.com/BloopAI/vibe-kanban · https://github.com/steveyegge/beads · https://github.com/eyaltoledano/claude-task-master
- **Arquivos:** beads (Go, CLI `bd`): `cmd/bd`, `claim.go`, `docs/`, `AGENT_INSTRUCTIONS.md`, `AGENTS.md` — "memory upgrade for your coding agent" com claim/ownership de tarefa.
- **Por que:** resolve o problema que quebra orquestração manual: dois agentes pegando a mesma tarefa. Kanban visual (vibe-kanban) para humano, claim transacional (beads) para o agente.

### 6. `dagger/container-use` — isolamento por container por agente — VM · 4.044★
- **URL:** https://github.com/dagger/container-use
- **Arquivos:** `mcpserver/tools.go`, `mcpserver/args.go`, `rules/agent.md`, `rules/cursor.mdc`, `rules/windsurf.mdc`, `examples/parallel.md`, `examples/services.md`, `environment/`
- **Por que:** worktree isola o git, não o ambiente; container-use dá stack completo por agente (com `examples/parallel.md` explícito) — o passo seguinte quando worktree começa a dar conflito de porta/dependência.

### 7. MCP — a camada de ferramentas entre CLIs — VA · servers 90.388★, python-sdk 24.314★
- **URLs:** https://github.com/modelcontextprotocol/servers · https://github.com/modelcontextprotocol/python-sdk · https://github.com/modelcontextprotocol/registry
- **Por que:** é o que faz a mesma skill/tool funcionar em claude, codex, opencode e hermes sem reescrever integração — o registry (7.256★) é onde achar servidores.
- **Crítica/contexto:** HN 738pts argumenta que Skills podem ser maiores que MCP (https://news.ycombinator.com/item?id=45619537); segurança de skills de terceiros é risco real — https://labs.reversec.com/posts/2026/05/skill-issues-compromising-claude-code-with-malicious-skills-agents-part-1

### 8. Frameworks programáticos (quando `tmux` não basta) — VA
- **URLs/★:** https://github.com/langchain-ai/langgraph (41.776) · https://github.com/openai/openai-agents-python (29.495) · https://github.com/crewAIInc/crewAI (58.662) · https://github.com/microsoft/autogen (61.006) · https://github.com/ag2ai/ag2 (4.933) · https://github.com/google/adk-python (21.554) · https://github.com/strands-agents/sdk-python (7.286) · https://github.com/openai/swarm (21.985, histórico/educacional)
- **Por que:** LangGraph é o único com grafo durável + checkpoint/retomada (o que um dev solo precisa para job longo que morre no meio); OpenAI Agents SDK/CrewAI para papéis; AutoGen/AG2 para conversa multiagente. Os demais são redundantes para 1 pessoa.
- **NAO_VALIDADO:** nenhum deles foi clonado nesta pesquisa — escolha por documentação, não por arquivos verificados.

### 9. Protocolos/ponte entre CLIs diferentes — VA · A2A 25.798★, claude-code-router 37.271★, agentapi 1.503★
- **URLs:** https://github.com/a2aproject/A2A · https://github.com/musistudio/claude-code-router · https://github.com/coder/agentapi
- **Por que:** o cenário real (claude + codex + opencode + hermes em paralelo) exige tradução: agentapi expõe HTTP para Claude Code/Goose/Aider/Gemini/Codex (dá para dirigir qualquer CLI por script) e claude-code-router centraliza roteamento de modelo/custo entre eles. A2A é o protocolo se você integrar com agentes de terceiros.
- **Posts:** HN 14pts Paseo (https://news.ycombinator.com/item?id=47530027, 17.473★ em https://github.com/getpaseo/paseo) — orquestrar múltiplos agentes de desktop+mobile.

### 10. Hermes Agent (a stack local) — VM · 246.155★
- **URL:** https://github.com/NousResearch/hermes-agent
- **Arquivos locais confirmados nesta máquina:** `/home/zes/.hermes/skills/autonomous-ai-agents/herdr-orchestrator/SKILL.md`, `/home/zes/.hermes/skills/software-development/herdr-pane-agents/SKILL.md`, `/home/zes/.hermes/skills/autonomous-ai-agents/hermes-agent/SKILL.md`
- **Por que:** é o único orquestrador deste documento que já está instalado e verificado *neste* workspace — `herdr-orchestrator` (times paralelos com review) e `herdr-pane-agents` (agente secundário em pane) cobrem o caso "claude/codex/opencode em paralelo" sem instalar nada novo.
- **Nota:** os outros agentes CLI relevantes para comparar: `sst/opencode` 207.901★, `openai/codex` 124.729★, `google-gemini/gemini-cli` 107.020★, `All-Hands-AI/OpenHands` 88.166★, `cline/cline` 68.289★, `block/goose` 54.361★, `Aider-AI/aider` 49.000★, `charmbracelet/crush` 28.132★, `RooCodeInc/Roo-Code` 24.304★, `SWE-agent/SWE-agent` 20.340★ (todos VA).

### Menções honrosas (orquestração)
| Item | URL | ★ | Nota |
|---|---|---|---|
| CCPM (GitHub Issues + worktrees) | https://github.com/automazeio/ccpm | 8.377 | PM que usa Issues como fila e worktree por tarefa (VA) |
| BMAD-METHOD | https://github.com/bmad-code-org/BMAD-METHOD | 53.104 | metodologia ágil agentica multi-papel (VA) |
| claude-flow | https://github.com/ruvnet/claude-flow | 72.626 | enxame/`swarm` com memória e federação (VA) |
| SuperClaude Framework | https://github.com/SuperClaude-Org/SuperClaude_Framework | 23.897 | comandos/personas sobre Claude Code (VA) |
| contexto | https://github.com/NeoLabHQ/context-engineering-kit | 1.702 | 44pts HN: técnicas de context engineering (VA) |
| config opinativa | https://github.com/trailofbits/claude-code-config | 2.113 | hardening real de Claude Code (VA) |
| descoberta | https://github.com/hesreallyhim/awesome-claude-code (54.171★) · https://github.com/davepoon/buildwithclaude (3.471★) · https://github.com/davila7/claude-code-templates (30.760★) | — | índices para não ficar garimpando |
| UI para agentes | https://github.com/21st-dev/1code | 5.598 | 75pts HN: UI tipo Cursor sobre Claude Code (VA) |
| worktree extra | https://github.com/golbin/gw (101★) · https://github.com/RPate97/lich (9★) | — | utilitários simples de worktree/stack por agente (VA) |
| specs | https://github.com/FredAntB/Spec-Driven-Development | 154 | 40pts HN: SDD como skill (VA) |

### Cobertura do pedido (checagem rápida)
`ui-designer` → item 6 (arquivo literal). `frontend-design` → item 1. `artifacts-builder` → item 2 (nome real `web-artifacts-builder`). Vercel/Next → item 3. shadcn/Tailwind → itens 2, 5, 10. Acessibilidade → item 5 (`wcag-audit-patterns`, `screen-reader-testing`). Responsividade → item 4 (`responsive-design` + container queries). Animações → item 3 (`react-view-transitions`) + menções (motion 33.618★, magicui 22.307★). Design review → itens 3 (`web-design-guidelines`) e 6 (`ui-ux-tester`). Playwright/E2E → item 7. Visual regression → item 10. Figma-to-code → item 8. Core Web Vitals → item 9. Orquestração: subagents/hooks/SDK → item 1; OpenCode/Codex/Crush/Cline/Roo/SWE-agent → menções; LangGraph/CrewAI/AutoGen/AG2/OpenAI Agents SDK → item 8; A2A/MCP → itens 7 e 9; worktrees/tmux/panes/fila/review cruzado → itens 2–6.

**Lacunas honestas:** (a) nenhuma skill oficial cobre "Core Web Vitals" — é tooling, não skill; (b) frameworks da Seção 2 item 8 foram validados só por API (sem clone); (c) revisão cruzada entre CLIs *diferentes* (ex.: Codex revisa o diff do Claude) não tem ferramenta dedicada consolidada — hoje se faz com `obra/superpowers` `requesting-code-review`/`receiving-code-review` + worktrees, ou `wshobson/agents` `plugins/agent-teams/skills/multi-reviewer-patterns/SKILL.md` (VM, arquivo confirmado no clone).
