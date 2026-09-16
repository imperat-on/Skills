# 01 — Coding Skills para Agentes CLI (Claude Code / Codex / OpenCode / Crush / Hermes)

> **Pesquisa validada — não é lista de memória.**
> Coleta: **2026-09-16** (17:55 -03) · Ambiente: Arch Linux, fish, `gh` autenticado como `imperat-on`
> Alvo: `/home/zes/Documents/projects/Skills` — kit portátil de skills **agnósticas de CLI**.

---

## 0. Método e o que foi de fato validado

| Passo | Ferramenta | Resultado |
|---|---|---|
| Star count / data de push / archive status | `gh api repos/OWNER/REPO --jq '.stargazers_count, .pushed_at, .description'` | ✅ 26 repos consultados ao vivo |
| Listagem real de arquivos | `git clone --depth 1` em `/tmp/skillsval` + `find -name SKILL.md` | ✅ 10 repos clonados e enumerados |
| Tamanho em linhas | `wc -l` sobre cada `SKILL.md` no clone | ✅ real, não estimado |
| Frontmatter (`name`, `description`) | `sed -n '1,12p'` nos arquivos clonados | ✅ 17 skills lidas |
| Comentário de comunidade (HN) | API Algolia `hn.algolia.com/api/v1/items/<id>` | ✅ threads e comentários reais |
| Comentário de comunidade (blogs) | `curl` + strip de HTML | ✅ 6 artigos extraídos |
| Comentário de comunidade (Reddit) | `curl` / browser real | ❌ **BLOQUEADO (HTTP 403)** |

### ⚠️ Limitações declaradas (leia antes de confiar cegamente)

1. **Reddit não foi acessível.** `www.reddit.com/...json`, `api.reddit.com`, `old.reddit.com` e o
   browser real retornaram **403 / "blocked by network security"**. As threads do Reddit citadas na
   seção 3 vieram do **índice de busca** (título + URL + trecho), **não** do corpo do thread.
   Estão marcadas `[índice]`. Não inventei conteúdo de comentário nenhum.
2. **`web_extract` indisponível** neste runtime (backend = ddgs, search-only). Todo fetch de página
   foi feito com `curl` + strip manual de HTML, e HN via API Algolia.
3. **Os números de stars são o que a API do GitHub retornou em 2026-09-16.** Alguns parecem
   inflados se comparados à memória histórica do ecossistema (ex.: `obra/superpowers`). Como o
   critério do Davi é "não inventar", transcrevi **literalmente** o retorno do `gh api` e sinalizo
   onde o número merece re-checagem antes de virar critério de decisão.
4. Onde **não** consegui validar o caminho exato de um `SKILL.md`, o item está marcado
   **`NAO_VALIDADO`**.

---

## 1. Repositórios-fonte validados (`gh api`, 2026-09-16)

### 1.1 Núcleo — contêm as skills de codificação

| Repo | Stars | Último push | Arquivos `SKILL.md` | Descrição (retorno literal da API) |
|---|---|---|---|---|
| [`obra/superpowers`](https://github.com/obra/superpowers) | 287594 | 2026-09-14 | **14** | An agentic skills framework & software development methodology that works. |
| [`anthropics/skills`](https://github.com/anthropics/skills) | 176699 | 2026-09-10 | **19** (+1 template) | Public repository for Agent Skills |
| [`mattpocock/skills`](https://github.com/mattpocock/skills) | 263548 | 2026-09-15 | **38** | Skills for Real Engineers. Straight from my .agents directory. |
| [`affaan-m/ECC`](https://github.com/affaan-m/ECC) (ex-`everything-claude-code`) | 260106 | 2026-09-15 | **292** (raiz) | The agent harness performance optimization system. Skills, instincts, memory, security, and research-first development for Claude Code, Codex, Opencode, Cursor and beyond. |
| [`wshobson/agents`](https://github.com/wshobson/agents) | 39728 | 2026-09-14 | **183** (84 plugins) | Multi-harness agentic plugin marketplace for Claude Code, Codex, Cursor, OpenCode, GitHub Copilot, Google Antigravity, and Pi |
| [`alirezarezvani/claude-skills`](https://github.com/alirezarezvani/claude-skills) | 26042 | 2026-08-30 | **846** | 380 Claude Code skills & agent skills & plugins … for Claude Code, Codex, Gemini CLI, Cursor, and 8 more coding agents |
| [`jeffallan/claude-skills`](https://github.com/Jeffallan/claude-skills) | 11557 | 2026-08-07 | **67** | 67 Specialized Skills for Full-Stack Developers. |
| [`getsentry/skills`](https://github.com/getsentry/skills) | 993 | 2026-09-07 | **27** | Agent Skills used by the Sentry team for development. |
| [`sickn33/agentic-awesome-skills`](https://github.com/sickn33/agentic-awesome-skills) | 46499 | 2026-09-16 | 2115+ (bundle) | AAS Core … 2,115+ agentic skills |
| [`sergiodxa/agent-skills`](https://github.com/sergiodxa/agent-skills) | 90 | 2026-02-01 | — | My own agent skills for tools I use |
| [`farmage/opencode-skills`](https://github.com/farmage/opencode-skills) | 166 | 2026-03-17 | 66 | 66 specialized AI skills + 9 workflow commands for OpenCode. Based on Claude Skills by jeffallan. |
| [`obra/superpowers-marketplace`](https://github.com/obra/superpowers-marketplace) | 1262 | 2026-09-08 | — | Curated Claude Code plugin marketplace |
| [`gsd-build/gsd-2`](https://github.com/gsd-build/gsd-2) | 7783 | 2026-05-22 | — | meta-prompting, context engineering and spec-driven development system |

### 1.2 Índices / agregadores (úteis para descoberta, não como fonte de skill)

| Repo | Stars | Push | Nota |
|---|---|---|---|
| [`hesreallyhim/awesome-claude-code`](https://github.com/hesreallyhim/awesome-claude-code) | 54171 | 2026-09-16 | Curadoria mais citada do ecossistema; atualiza quase diariamente |
| [`ComposioHQ/awesome-claude-skills`](https://github.com/ComposioHQ/awesome-claude-skills) | 75208 | 2026-08-10 | Curadoria |
| [`davila7/claude-code-templates`](https://github.com/davila7/claude-code-templates) | 30760 | 2026-09-16 | CLI de config; **copia** skills de terceiros (ver §3) |
| [`agentskills/agentskills`](https://github.com/agentskills/agentskills) | 25410 | 2026-08-09 | **Especificação** do padrão Agent Skills — leitura obrigatória p/ escrever skill portátil |
| [`VoltAgent/awesome-claude-code-subagents`](https://github.com/VoltAgent/awesome-claude-code-subagents) | 25126 | 2026-09-14 | 100+ subagents — **0 arquivos `SKILL.md`** (formato `agents/*.md`), não serve ao kit de skills |
| [`travisvn/awesome-claude-skills`](https://github.com/travisvn/awesome-claude-skills) | 15096 | 2026-04-28 | Curadoria, push mais antigo (menos ativa) |
| [`BehiSecc/awesome-claude-skills`](https://github.com/BehiSecc/awesome-claude-skills) | 10152 | 2026-08-02 | Curadoria |
| [`ChrisWiles/claude-code-showcase`](https://github.com/ChrisWiles/claude-code-showcase) | 6070 | 2026-01-06 | Exemplo de config de projeto |
| [`davepoon/buildwithclaude`](https://github.com/davepoon/buildwithclaude) | 3471 | 2026-09-15 | Hub; 382 `SKILL.md` mas majoritariamente integrações SaaS |
| [`majiayu000/claude-skill-registry`](https://github.com/majiayu000/claude-skill-registry) | 618 | 2026-09-16 | Registro com busca web |
| [`karanb192/awesome-claude-skills`](https://github.com/karanb192/awesome-claude-skills) | 515 | 2026-09-01 | "50+ verified skills" — **0 `SKILL.md`** no clone (é lista, não pacote) |
| [`aidankinzett/claude-git-pr-skill`](https://github.com/aidankinzett/claude-git-pr-skill) | 50 | 2025-12-02 | Skill isolada de PR review |
| [`anthroos/claude-code-review-skill`](https://github.com/anthroos/claude-code-review-skill) | 40 | 2026-02-27 | Skill isolada de code review |
| [`Dilaz/security-review-skill`](https://github.com/Dilaz/security-review-skill) | 7 | 2026-02-03 | Skill isolada, pouca tração |
| [`steipete/agent-rules`](https://github.com/steipete/agent-rules) | 5688 | 2026-05-03 | ⛔ **ARCHIVED** — não usar |

---

## 2. Skills de codificação por área

Legenda: **nome** · repo · caminho exato do `SKILL.md` · o que resolve · **linhas** (validadas via `wc -l`).

### 2.1 Implementação de features

| Skill | Repo | Caminho do `SKILL.md` | Resolve | Linhas |
|---|---|---|---|---|
| `brainstorming` | [obra/superpowers](https://github.com/obra/superpowers) | `skills/brainstorming/SKILL.md` | Explora intenção/requisitos/design antes de qualquer código; classifica quanto processo a tarefa exige | 250 |
| `writing-plans` | obra/superpowers | `skills/writing-plans/SKILL.md` | Plano de implementação em tarefas bite-sized, assumindo engenheiro sem contexto do repo | 171 |
| `subagent-driven-development` | obra/superpowers | `skills/subagent-driven-development/SKILL.md` | 1 subagente implementador fresco por tarefa + review por tarefa + review final amplo | **568** |
| `using-git-worktrees` | obra/superpowers | `skills/using-git-worktrees/SKILL.md` | Isola cada feature em worktree git → tarefas paralelas sem colisão | 167 |
| `dispatching-parallel-agents` | obra/superpowers | `skills/dispatching-parallel-agents/SKILL.md` | Padrão de fan-out/fan-in de subagentes | 167 |
| `implementation-planning` / `to-spec` / `to-tickets` | mattpocock/skills | `skills/engineering/to-spec/SKILL.md`, `skills/engineering/to-tickets/SKILL.md` | Converte ideia → spec → tickets executáveis | 75 / 105 |
| `spec-driven-workflow` | alirezarezvani/claude-skills | `engineering/skills/spec-driven-workflow/SKILL.md` | Fluxo spec-first ponta a ponta | 333 |
| `feature-forge` | jeffallan/claude-skills | `skills/feature-forge/SKILL.md` | Da ideia à feature implementada com padrão do time | 100 |
| `focused-fix` | alirezarezvani/claude-skills | `engineering/skills/focused-fix/SKILL.md` | Correção cirúrgica escopada, sem refactor colateral | 318 |
| `plan-canvas` | affaan-m/ECC | `skills/plan-canvas/SKILL.md` | Canvas de planejamento antes de executar | 198 |
| `plan-orchestrate` | affaan-m/ECC | `skills/plan-orchestrate/SKILL.md` | Orquestração de planos multi-etapa | 263 |
| `before-you-build` | wshobson/agents | `plugins/before-you-build/skills/before-you-build/SKILL.md` | Triagem de pré-implementação (evitar construir a coisa errada) | 50 |
| `spec-miner` | jeffallan/claude-skills | `skills/spec-miner/SKILL.md` | Extrai a spec real de um codebase existente | 110 |

### 2.2 Code review

| Skill | Repo | Caminho do `SKILL.md` | Resolve | Linhas |
|---|---|---|---|---|
| `code-review-excellence` | wshobson/agents | `plugins/developer-essentials/skills/code-review-excellence/SKILL.md` | Review em **4 fases cronometradas** (contexto 2-3min → alto nível 5-10 → linha-a-linha 10-20 → decisão 2-3); checklist de segurança e de performance; deixa nitpick de formatação para o linter | **529** |
| `code-review` (Sentry) | [getsentry/skills](https://github.com/getsentry/skills) | `skills/code-review/SKILL.md` | Review de PR no padrão do time Sentry | 102 |
| `code-review` (2 eixos) | mattpocock/skills | `skills/engineering/code-review/SKILL.md` | Diff vs ponto fixo em **2 eixos paralelos**: *Standards* (padrões do repo) e *Spec* (bate com a issue?) | 87 |
| `pr-review-expert` | alirezarezvani/claude-skills | `engineering/skills/pr-review-expert/SKILL.md` | Review de PR orientado a risco | 397 |
| `requesting-code-review` | obra/superpowers | `skills/requesting-code-review/SKILL.md` | Dispara subagente revisor **sem herdar o histórico da sessão** (contexto limpo é o ponto) | 95 |
| `receiving-code-review` | obra/superpowers | `skills/receiving-code-review/SKILL.md` | Como **responder** a review sem defensividade nem over-compliance | 205 |
| `code-reviewer` | jeffallan/claude-skills | `skills/code-reviewer/SKILL.md` | Review amplo: bugs, SQLi/XSS/deserialização insegura, code smells, N+1 | 121 |
| `code-reviewer` | alirezarezvani/claude-skills | `engineering-team/skills/code-reviewer/SKILL.md` | Review report estruturado e priorizado | 183 |
| `multi-reviewer-patterns` | wshobson/agents | `plugins/agent-teams/skills/multi-reviewer-patterns/SKILL.md` | N revisores em paralelo com papéis distintos | 127 |
| `gh-review-requests` | getsentry/skills | `skills/gh-review-requests/SKILL.md` | Triagem das reviews pendentes no GitHub | 79 |
| `adversarial-reviewer` | alirezarezvani/claude-skills | `engineering-team/skills/adversarial-reviewer/SKILL.md` | Review adversarial (ataca a própria solução) | 247 |
| `named-persona-adversarial-review` | alirezarezvani/claude-skills | `engineering-team/skills/named-persona-adversarial-review/SKILL.md` | Review adversarial com persona nomeada | 162 |
| `iterate-pr` | getsentry/skills | `skills/iterate-pr/SKILL.md` | Loop de iteração sobre comentários de PR | 145 |
| `review-agent-setup` | wshobson/agents | `plugins/review-agent-governance/skills/review-agent-setup/SKILL.md` | Governança de agente revisor | 170 |

> ⚠️ Em `wshobson/agents`, os plugins `comprehensive-review`, `code-refactoring`, `git-pr-workflows`,
> `tdd-workflows`, `unit-testing`, `error-diagnostics`, `database-migrations`, `performance-testing-review`
> e `application-performance` **não contêm `SKILL.md`** — só `commands/` + `agents/`. Não os conte como skills.

### 2.3 Debugging / root cause

| Skill | Repo | Caminho do `SKILL.md` | Resolve | Linhas |
|---|---|---|---|---|
| `systematic-debugging` | obra/superpowers | `skills/systematic-debugging/SKILL.md` | **"ALWAYS find root cause before attempting fixes. Symptom fixes are failure."** Proíbe fix no ponto do sintoma | 283 |
| `debugging-strategies` | wshobson/agents | `plugins/developer-essentials/skills/debugging-strategies/SKILL.md` | Técnicas sistemáticas + profiling + análise de causa raiz agnóstica de stack | **527** |
| `diagnosing-bugs` | mattpocock/skills | `skills/engineering/diagnosing-bugs/SKILL.md` | Loop de diagnóstico p/ bugs difíceis e **regressões de performance**; inclui fase de *Redact* (sanitizar dados) | 138 |
| `debugging-wizard` | jeffallan/claude-skills | `skills/debugging-wizard/SKILL.md` | Debug guiado por sintoma → causa | 107 |
| `parallel-debugging` | wshobson/agents | `plugins/agent-teams/skills/parallel-debugging/SKILL.md` | Várias hipóteses investigadas em subagentes paralelos | 133 |
| `find-bugs` | getsentry/skills | `skills/find-bugs/SKILL.md` | Caça a bugs com foco em sinal, não ruído | 75 |
| `verification-before-completion` | obra/superpowers | `skills/verification-before-completion/SKILL.md` | **"Evidence before claims, always."** Roda comando de verificação e mostra output **antes** de dizer "pronto" | 120 |
| `agent-introspection-debugging` | affaan-m/ECC | `skills/agent-introspection-debugging/SKILL.md` | Debug de sessão do próprio agente | 154 |
| `error-diagnostics` | wshobson/agents | *(plugin existe, sem `SKILL.md`)* | **NAO_VALIDADO** como skill | — |

### 2.4 Testes / TDD

| Skill | Repo | Caminho do `SKILL.md` | Resolve | Linhas |
|---|---|---|---|---|
| `test-driven-development` | obra/superpowers | `skills/test-driven-development/SKILL.md` | **"If you didn't watch the test fail, you don't know if it tests the right thing."** Red→green com falha observada | 320 |
| `tdd` | mattpocock/skills | `skills/engineering/tdd/SKILL.md` | Referência enxuta do red→green: o que é teste bom, onde mora, anti-padrões | **38** |
| `javascript-testing-patterns` | wshobson/agents | `plugins/javascript-typescript/skills/javascript-testing-patterns/SKILL.md` | Vitest/Jest, mocks, testes de integração | **537** |
| `python-testing-patterns` | wshobson/agents | `plugins/python-development/skills/python-testing-patterns/SKILL.md` | pytest, fixtures, parametrize | 278 |
| `test-master` | jeffallan/claude-skills | `skills/test-master/SKILL.md` | Estratégia de teste especializada | 96 |
| `tdd-guide` | alirezarezvani/claude-skills | `engineering-team/skills/tdd-guide/SKILL.md` | Guia TDD | **NAO_VALIDADO (linhas)** — arquivo confirmado no clone, contagem não coletada |
| `e2e-testing-patterns` | wshobson/agents | `plugins/developer-essentials/skills/e2e-testing-patterns/SKILL.md` | E2E estável (anti-flaky) | 127 |
| `webapp-testing` | anthropics/skills | `skills/webapp-testing/SKILL.md` | Playwright + helper `scripts/with_server.py` p/ testar app local | 95 |
| `playwright-expert` | jeffallan/claude-skills | `skills/playwright-expert/SKILL.md` | Playwright de produção | 171 |
| `ai-regression-testing` | affaan-m/ECC | `skills/ai-regression-testing/SKILL.md` | Regressão em features com IA | 386 |
| `tdd-workflow` | affaan-m/ECC | `skills/tdd-workflow/SKILL.md` | Fluxo TDD completo por stack | 583 |
| `python-testing` | affaan-m/ECC | `skills/python-testing/SKILL.md` | TDD Python (versão ECC) | 817 |
| `golang-testing` / `rust-testing` / `kotlin-testing` | affaan-m/ECC | `skills/<lang>-testing/SKILL.md` | TDD por linguagem | 721 / 501 / 825 |
| `verification-loop` | affaan-m/ECC | `skills/verification-loop/SKILL.md` | Loop curto de verificação contínua | 129 |
| `bats-testing-patterns` | wshobson/agents | `plugins/shell-scripting/skills/bats-testing-patterns/SKILL.md` | Testes de shell script | 229 |

### 2.5 Refactor / saúde de código

| Skill | Repo | Caminho do `SKILL.md` | Resolve | Linhas |
|---|---|---|---|---|
| `improve-codebase-architecture` | mattpocock/skills | `skills/engineering/improve-codebase-architecture/SKILL.md` | Melhora a arquitetura existente sem reescrever | 71 |
| `code-simplifier` | getsentry/skills | `skills/code-simplifier/SKILL.md` | Simplificação de código pós-implementação | 119 |
| `codebase-design` | mattpocock/skills | `skills/engineering/codebase-design/SKILL.md` | Critérios de design de codebase | 114 |
| `python-anti-patterns` | wshobson/agents | `plugins/python-development/skills/python-anti-patterns/SKILL.md` | Anti-padrões Python a remover | 349 |
| `plankton-code-quality` | affaan-m/ECC | `skills/plankton-code-quality/SKILL.md` | Gate de qualidade de código | 237 |
| `tech-debt-tracker` | alirezarezvani/claude-skills | `engineering/skills/tech-debt-tracker/SKILL.md` | Dívida técnica rastreada | 87 |
| `legacy-modernizer` | jeffallan/claude-skills | `skills/legacy-modernizer/SKILL.md` | Modernização de legado | 139 |
| `code-refactoring` | wshobson/agents | *(sem `SKILL.md`)* | **NAO_VALIDADO** como skill | — |

### 2.6 Segurança

| Skill | Repo | Caminho do `SKILL.md` | Resolve | Linhas |
|---|---|---|---|---|
| `security-review` | **[getsentry/skills](https://github.com/getsentry/skills)** | `skills/security-review/SKILL.md` | ⭐ **A melhor do levantamento.** Não é checklist: é **metodologia** — sistema de confiança (HIGH só com input controlado pelo atacante confirmado; MEDIUM; LOW), consciência de falso-positivo (`settings.X` é server-side, não input), análise de fluxo de dados antes de reportar, e **~20 arquivos de referência** (17 vulns + `languages/python.md`, `languages/javascript.md`, `infrastructure/docker.md`) | **312** + refs |
| `security-review` | affaan-m/ECC (ex-`everything-claude-code`) | `skills/security-review/SKILL.md` | O original que circulou muito — 10 domínios em checklist. Crítica: estático, exemplos só TS/Next/Supabase, seção Solana estranha | 504 |
| `security-reviewer` | jeffallan/claude-skills | `skills/security-reviewer/SKILL.md` | Relatório de auditoria com severidade + remediação | 105 |
| `secure-code-guardian` | jeffallan/claude-skills | `skills/secure-code-guardian/SKILL.md` | Guardrails de código seguro | 193 |
| `sast-configuration` | wshobson/agents | `plugins/security-scanning/skills/sast-configuration/SKILL.md` | Configurar SAST | 192 |
| `stride-analysis-patterns` | wshobson/agents | `plugins/security-scanning/skills/stride-analysis-patterns/SKILL.md` | STRIDE | 66 |
| `attack-tree-construction` | wshobson/agents | `plugins/security-scanning/skills/attack-tree-construction/SKILL.md` | Árvores de ataque | 74 |
| `threat-mitigation-mapping` | wshobson/agents | `plugins/security-scanning/skills/threat-mitigation-mapping/SKILL.md` | Mapa ameaça→mitigação | 82 |
| `security-requirement-extraction` | wshobson/agents | `plugins/security-scanning/skills/security-requirement-extraction/SKILL.md` | Requisitos de segurança a partir do código | 67 |
| `gha-security-review` | getsentry/skills | `skills/gha-security-review/SKILL.md` | Segurança de GitHub Actions: pwn-request, expression injection, escalada de credencial, runner infra, ataques reais | 192 |
| `skill-security-auditor` | alirezarezvani/claude-skills | `engineering/skills/skill-security-auditor/SKILL.md` | Auditar a **própria skill** antes de instalar (essencial para kit portátil) | 171 |
| `skill-scanner` | getsentry/skills | `skills/skill-scanner/SKILL.md` | Scanner de segurança de skill | 209 |
| `owasp-security-check` | sergiodxa/agent-skills | — (`sergiodxa/agent-skills`) | 20 regras OWASP em 5 categorias de prioridade, 1 arquivo por regra; críticas: exemplos TypeScript-only, sem filtro de falso-positivo | **NAO_VALIDADO (linhas)** |
| `senior-security` | alirezarezvani/claude-skills | `engineering-team/skills/senior-security/SKILL.md` | ⚠️ É toolkit de **threat modeling** (STRIDE/DREAD), **não** review de código | **NAO_VALIDADO (linhas)** |
| `security-review` | davila7/claude-code-templates | — | Cópia do skill do affaan-m + 2 linhas de frontmatter. Atribuído, mas não agrega | **NAO_VALIDADO** |

### 2.7 Performance

| Skill | Repo | Caminho do `SKILL.md` | Resolve | Linhas |
|---|---|---|---|---|
| `python-performance-optimization` | wshobson/agents | `plugins/python-development/skills/python-performance-optimization/SKILL.md` | Profiling e otimização Python | 100 |
| `react-performance` | affaan-m/ECC | `skills/react-performance/SKILL.md` | Performance React | 575 |
| `performance-profiler` | alirezarezvani/claude-skills | `engineering/skills/performance-profiler/SKILL.md` | Profiling genérico | 74 |
| `django-perf-review` | getsentry/skills | `skills/django-perf-review/SKILL.md` | Review de perf Django (N+1, queries) | 396 |
| `sql-optimization-patterns` | wshobson/agents | `plugins/developer-essentials/skills/sql-optimization-patterns/SKILL.md` | Otimização SQL | 214 |
| `cost-optimization` | wshobson/agents | `plugins/cloud-infrastructure/skills/cost-optimization/SKILL.md` | Custo de cloud | 313 |
| `slo-implementation` | wshobson/agents | `plugins/observability-monitoring/skills/slo-implementation/SKILL.md` | SLOs | 274 |

### 2.8 Git / PR workflow

| Skill | Repo | Caminho do `SKILL.md` | Resolve | Linhas |
|---|---|---|---|---|
| `finishing-a-development-branch` | obra/superpowers | `skills/finishing-a-development-branch/SKILL.md` | Fechamento de branch: limpeza, PR, merge | 225 |
| `git-advanced-workflows` | wshobson/agents | `plugins/developer-essentials/skills/git-advanced-workflows/SKILL.md` | Rebase interativo, bisect, reflog, recuperação | 198 |
| `git-workflow` | affaan-m/ECC | `skills/git-workflow/SKILL.md` | Fluxo git completo (o mais longo da categoria) | 716 |
| `git-worktree-manager` | alirezarezvani/claude-skills | `engineering/skills/git-worktree-manager/SKILL.md` | Gestão de worktrees paralelos | 193 |
| `commit` | getsentry/skills | `skills/commit/SKILL.md` | Commits com mensagem consistente | 62 |
| `create-branch` | getsentry/skills | `skills/create-branch/SKILL.md` | Branch conforme convenção | 68 |
| `pr-writer` | getsentry/skills | `skills/pr-writer/SKILL.md` | Descrição de PR completa | 160 |
| `pr-link-issue` | getsentry/skills | `skills/pr-link-issue/SKILL.md` | Fecha o ciclo PR↔issue | 74 |
| `resolving-merge-conflicts` | mattpocock/skills | `skills/engineering/resolving-merge-conflicts/SKILL.md` | Resolver conflito sem perder semântica | **14** |
| `git-guardrails-claude-code` | mattpocock/skills | `skills/misc/git-guardrails-claude-code/SKILL.md` | Guardrails contra git destrutivo | 95 |
| `setup-pre-commit` | mattpocock/skills | `skills/misc/setup-pre-commit/SKILL.md` | Instalar pre-commit | 91 |
| `github-ops` | affaan-m/ECC | `skills/github-ops/SKILL.md` | Operações GitHub | **NAO_VALIDADO (linhas)** |
| PR review skill isolada | [aidankinzett/claude-git-pr-skill](https://github.com/aidankinzett/claude-git-pr-skill) | repo | PR review com pending reviews + sugestões + aprovação do usuário | **NAO_VALIDADO** |
| code review skill isolada | [anthroos/claude-code-review-skill](https://github.com/anthroos/claude-code-review-skill) | repo | Alternativa gratuita ao CodeRabbit | **NAO_VALIDADO** |

### 2.9 Banco de dados

| Skill | Repo | Caminho do `SKILL.md` | Resolve | Linhas |
|---|---|---|---|---|
| `sql-database-assistant` | alirezarezvani/claude-skills | `engineering/skills/sql-database-assistant/SKILL.md` | Assistência SQL/database | 457 |
| `database-migrations` | affaan-m/ECC | `skills/database-migrations/SKILL.md` | Migrações seguras (expand/contract) | 430 |
| `database-migration` | wshobson/agents | `plugins/framework-migration/skills/database-migration/SKILL.md` | Migração de banco | 333 |
| `postgresql-table-design` | wshobson/agents | `plugins/database-design/skills/postgresql-table-design/SKILL.md` | Modelagem de tabela Postgres | 129 |
| `database-designer` | alirezarezvani/claude-skills | `engineering/skills/database-designer/SKILL.md` | Design de esquema | 314 |
| `database-schema-designer` | alirezarezvani/claude-skills | `engineering/skills/database-schema-designer/SKILL.md` | Esquema com normalização | 248 |
| `postgres-pro` | jeffallan/claude-skills | `skills/postgres-pro/SKILL.md` | Postgres avançado | 154 |
| `sql-pro` | jeffallan/claude-skills | `skills/sql-pro/SKILL.md` | SQL avançado | 131 |
| `database-optimizer` | jeffallan/claude-skills | `skills/database-optimizer/SKILL.md` | Otimização de queries | 149 |

### 2.10 API / backend

| Skill | Repo | Caminho do `SKILL.md` | Resolve | Linhas |
|---|---|---|---|---|
| `api-design` | affaan-m/ECC | `skills/api-design/SKILL.md` | Design de API completo | 524 |
| `api-design-reviewer` | alirezarezvani/claude-skills | `engineering/skills/api-design-reviewer/SKILL.md` | Audita contrato de API | 432 |
| `api-design-principles` | wshobson/agents | `plugins/backend-development/skills/api-design-principles/SKILL.md` | Princípios de design | 110 |
| `api-designer` | jeffallan/claude-skills | `skills/api-designer/SKILL.md` | API REST tipada | 219 |
| `mcp-builder` | anthropics/skills | `skills/mcp-builder/SKILL.md` | Construir servidor MCP de qualidade (Python FastMCP **ou** Node/TS SDK) | 236 |
| `architecture-patterns` | wshobson/agents | `plugins/backend-development/skills/architecture-patterns/SKILL.md` | Clean/hexagonal, camadas | 164 |
| `microservices-patterns` | wshobson/agents | `plugins/backend-development/skills/microservices-patterns/SKILL.md` | Padrões de microserviço | 90 |
| `cqrs-implementation` | wshobson/agents | `plugins/backend-development/skills/cqrs-implementation/SKILL.md` | CQRS | 79 |
| `saga-orchestration` | wshobson/agents | `plugins/backend-development/skills/saga-orchestration/SKILL.md` | Saga distribuída | 117 |
| `fastapi-templates` | wshobson/agents | `plugins/api-scaffolding/skills/fastapi-templates/SKILL.md` | Scaffold FastAPI | 136 |
| `api-test-suite-builder` | alirezarezvani/claude-skills | `engineering/skills/api-test-suite-builder/SKILL.md` | Suite de teste de API | 177 |
| `document-api-endpoint` | getsentry/skills | `skills/document-api-endpoint/SKILL.md` | Doc de endpoint | 53 |
| `openapi-spec-generation` | wshobson/agents | `plugins/documentation-generation/skills/openapi-spec-generation/SKILL.md` | Gerar OpenAPI | 66 |
| `graphql-architect` / `websocket-engineer` | jeffallan/claude-skills | `skills/graphql-architect/SKILL.md`, `skills/websocket-engineer/SKILL.md` | GraphQL / WebSocket | 148 / 170 |

### 2.11 Migração / upgrade

| Skill | Repo | Caminho do `SKILL.md` | Resolve | Linhas |
|---|---|---|---|---|
| `migration-architect` | alirezarezvani/claude-skills | `engineering/skills/migration-architect/SKILL.md` | Plano de migração arquitetural | 428 |
| `dependency-upgrade` | wshobson/agents | `plugins/framework-migration/skills/dependency-upgrade/SKILL.md` | Bump de dependências com segurança | 368 |
| `react-modernization` | wshobson/agents | `plugins/framework-migration/skills/react-modernization/SKILL.md` | React legado → moderno | 328 |
| `angular-migration` | wshobson/agents | `plugins/framework-migration/skills/angular-migration/SKILL.md` | Migração Angular | 313 |
| `legacy-modernizer` | alirezarezvani/claude-skills | `engineering/skills/legacy-modernizer/SKILL.md` | Modernização de legado | **NAO_VALIDADO (linhas)** |
| `migrate-to-shoehorn` | mattpocock/skills | `skills/misc/migrate-to-shoehorn/SKILL.md` | Migração pontual TS | 118 |

### 2.12 Documentação técnica

| Skill | Repo | Caminho do `SKILL.md` | Resolve | Linhas |
|---|---|---|---|---|
| `architecture-decision-records` | wshobson/agents | `plugins/documentation-generation/skills/architecture-decision-records/SKILL.md` | ADRs que sobrevivem ao tempo | **441** |
| `doc-coauthoring` | anthropics/skills | `skills/doc-coauthoring/SKILL.md` | Co-autoria de doc com o humano | 375 |
| `code-documenter` | jeffallan/claude-skills | `skills/code-documenter/SKILL.md` | Doc inline/API | 149 |
| `changelog-automation` | wshobson/agents | `plugins/documentation-generation/skills/changelog-automation/SKILL.md` | Changelog automático | 119 |
| `changelog-generator` | alirezarezvani/claude-skills | `engineering/skills/changelog-generator/SKILL.md` | Changelog por commits | 203 |
| `agents-md` | getsentry/skills | `skills/agents-md/SKILL.md` | Escrever `AGENTS.md` que funciona | 95 |
| `codebase-onboarding` | alirezarezvani/claude-skills | `engineering/skills/codebase-onboarding/SKILL.md` | Onboarding em repo desconhecido | 84 |
| `runbook-generator` | alirezarezvani/claude-skills | `engineering/skills/runbook-generator/SKILL.md` | Runbooks operacionais | 76 |

### 2.13 Meta — escrever/validar as próprias skills (crítico p/ o kit do Davi)

| Skill | Repo | Caminho do `SKILL.md` | Resolve | Linhas |
|---|---|---|---|---|
| `skill-creator` | anthropics/skills | `skills/skill-creator/SKILL.md` | Criar, editar, medir performance de skills; rodar evals e otimizar a `description` p/ melhor triggering | **485** |
| `writing-skills` | obra/superpowers | `skills/writing-skills/SKILL.md` | O guia mais longo do ecossistema sobre escrever skill | **679** |
| `using-superpowers` | obra/superpowers | `skills/using-superpowers/SKILL.md` | Bootstrap do framework | 63 |
| `skill-writer` | getsentry/skills | `skills/skill-writer/SKILL.md` | Escrever skill no padrão Sentry | 156 |
| `writing-for-agents` | mattpocock/skills | `skills/productivity/writing-for-agents/SKILL.md` | Prosa técnica que um agente executa | 81 |
| `agent-skills-spec` | agentskills/agentskills | `agent-skills-spec.md` | **Especificação** do formato (fonte de verdade p/ portabilidade) | — |

---

## 3. O que a comunidade dev realmente disse (com links)

### 3.1 Superpowers — o mais elogiado *e* o mais criticado

**Elogios**

- **[HN #47623101 — "A Rave Review of Superpowers (For Claude Code)"](https://news.ycombinator.com/item?id=47623101)**
  (50 pts, 25 comentários). Autor [Evan Schwartz](https://emschwartz.me/a-rave-review-of-superpowers-for-claude-code/):
  *"Using Claude Code with Superpowers is so much more productive and the features it builds are so
  much more correct than with stock Claude Code. I cannot recommend it enough."*
  Fluxo: Brainstorming → Options/Tradeoffs → Plan Sketch → Design Doc → Implementation Plan → Implementation Steps.
- **[blog.fsck.com — Jesse Vincent, o autor](https://blog.fsck.com/2025/10/09/superpowers/)**
  ([HN #45547344](https://news.ycombinator.com/item?id=45547344), **435 pts**) — explica o bootstrap via
  session-start-hook e o workflow brainstorm→plan→implement.
- **[Simon Willison](https://simonwillison.net/2025/Oct/10/superpowers/)** (10/10/2025):
  *"Jesse is one of the most creative users of coding agents (Claude Code in particular) that I know.
  […] There's a lot in here!"* — e destaca o `skills/debugging/root-cause-tracing/SKILL.md` com grafo Graphviz.
- **[Ask HN #46343801](https://news.ycombinator.com/item?id=46343801)** — usuário `linesofcode`:
  *"Superpowers is amazing."*; `mithras`: *"Playwright, so Claude can test end to end and iterate."*

**Críticas reais (mesmo thread HN #47623101)**

- `d--b`: *"I personally don't like superpowers very much. My boss does. I think Claude makes more
  mistakes when using superpowers than when not. […] Just don't believe it's a silver bullet. It's still
  the same Claude."*
- `raesene9` sobre o instalador para Codex/OpenCode: *"it's like curl|bash but with added LLM agents…"*
  (risco de supply chain — relevante para o kit portátil).
- `JohnCClarke`: *"Online reviews indicate that Superpowers is best for people who are not already
  experienced SW development managers. Is that true?"* — i.e. possível overhead para sênior.
- `deaux`: reclama que falta flexibilidade até no Plan Sketch (*"IMO Superpowers isn't the ideal
  solution because it too lacks flexibility"*).
- **[r/ClaudeCode — "Are you guys still using the superpowers skill?"](https://www.reddit.com/r/ClaudeCode/comments/1u2tqud/are_you_guys_still_using_the_superpowers_skill/)** `[índice]`
  — questiona se ainda vale com modelos novos ("Ultracode").
- **[r/Anthropic — "is Superpowers plugin/skill relevant today"](https://www.reddit.com/r/Anthropic/comments/1uas21o/is_superpowers_pluginskill_relevant_today/)** `[índice]` — mesma dúvida de obsolescência.
- **[r/ClaudeAI — "Is the superpowers skill worth it on a Pro plan?"](https://www.reddit.com/r/ClaudeAI/comments/1uatdmp/is_the_superpowers_skill_worth_it_on_a_pro_plan/)** `[índice]` — custo em tokens.
- **[r/codex — "Superpowers, is it really worth it?"](https://www.reddit.com/r/codex/comments/1to6329/superpowers_is_it_really_worth_it/)** `[índice]`
- **[r/ClaudeCode — "Superpowers explained: the popular Claude plugin that enforces TDD, subagents, and planning"](https://www.reddit.com/r/ClaudeCode/comments/1qi7rpc/superpowers_explained_the_popular_claude_plugin/)** `[índice]`
  — tese central: *"The problem with coding agents isn't capability — it's discipline."*
- **[mcp.directory — "Superpowers for Claude Code: Still Worth It in 2026?"](https://mcp.directory/blog/superpowers-skill-worth-it-2026)**
  — veredito matizado + recomendação de instalação modular em vez do plugin inteiro.

> **Nuance importante:** o skill de root-cause-tracing que o Simon Willison citou em 2025 com o caminho
> `skills/debugging/root-cause-tracing/SKILL.md` **não existe mais** no `main` clonado em 2026-09-16 —
> hoje está consolidado em `skills/systematic-debugging/SKILL.md`. Links antigos quebram.

### 3.2 wshobson/agents — "o melhor repo gratuito para engenheiros", com ressalva de escala

- **[ClaudeKit — "wshobson/agents Review: 192 Free Agents, Honestly Assessed"](https://theclaudekit.com/blog/wshobson-agents-review-192-tested)**
  (20/04/2026, com disclosure de que vendem produto concorrente):
  - Elogio: *"the best free Claude Code agent repository for software engineers"*; elogia **isolamento de
    contexto por plugin** e **export multi-harness** (um fonte Markdown → Claude Code, Cursor, Codex CLI,
    OpenCode, Gemini CLI).
  - Crítica: *"quality variance across that scale, no per-component token measurement, and breadth over
    vertical depth."*
  - Também elogia o **tiering de modelo em 4 níveis** (Opus para review de arquitetura/segurança → Haiku
    para tarefas operacionais).
- **[r/ClaudeCode — "I am searching for a set of claude agents that's actually tested not garbage"](https://www.reddit.com/r/ClaudeCode/comments/1pwp9qt/i_am_searching_for_a_set_of_claude_agents_thats/)** `[índice]`
  — a resposta mais votada recomenda `wshobson/agents`: *"Not mine, but I'm using this one for quite some time…"*
- **[r/ClaudeAI — "Effective use of subagents"](https://www.reddit.com/r/ClaudeAI/comments/1mey55y/effective_use_of_subagents/)** `[índice]` — cita o padrão de orquestração do wshobson.
- **[claudeskills.info — página do `code-review-excellence`](https://claudeskills.info/skills/wshobson/agents/code-review-excellence/)**
  — descreve as 4 fases cronometradas e o fato de a skill deliberadamente excluir nitpick de formatação.
- **[skills.rest](https://skills.rest/skill/code-review-excellence-wshobson)** / **[skillstore.io](https://skillstore.io/skills/wshobson-code-review-excellence)** — listagens espelho.

### 3.3 mattpocock/skills — popular, mas com crítica dura

- **[HN #49529329 — "AI Coding Agent Skills for Real Engineers"](https://news.ycombinator.com/item?id=49529329)** (43 pts, 14 com.).
  - `hungryhobbit`: *"If I had a nickel for every dev who has written a 'productivity suite' of skills,
    and shared it with others as if it was a burst of innovation… (when it's really extremely specific
    to that dev and their workflow)."*
  - `clickety_clack`: *"it seems like all this could be one moderately-sized AGENTS.md/CLAUDE.md, and much
    of it doesn't need to be detailed at all."*
  - `mock-possum`: *"it's just easier to build it as you go. […] Trying to start with these preset banks
    of instructions just never seems like it works out in the long run."*
  - `Supermancho`: crítica mais ácida — *"a hand-wavy approach to engineering in a silo"*.
  - `codeduck`: *"Christ, this is exhausting."*
  - Elogio indireto: 263k stars e um "Show HN" de terceiro só para rodar essas skills em lote AFK
    ([HN #49314342](https://news.ycombinator.com/item?id=49314342)).

### 3.4 Segurança — review comparativo de 5 skills

- **[TimOnWeb — "I Checked 5 Security Skills for Claude Code. Only One Is Worth Installing"](https://timonweb.com/ai/i-checked-5-security-skills-for-claude-code-only-one-is-worth-installing/)**
  (25/02/2026) ([HN #47149897](https://news.ycombinator.com/item?id=47149897)). Resumo fiel do artigo:
  - *"Don't sort by install count"* — o mais instalado (`sickn33/antigravity-awesome-skills@security-review`,
    1.600+ installs) é **cópia verbatim** de outro skill, distribuída em bundle de 900+ skills. *"install
    count is a distribution metric, not a quality signal."* → ⚠️ **o repo hoje se chama
    `sickn33/agentic-awesome-skills`** (validado: 46.499 stars, 2115+ skills), ou seja o artigo já está desatualizado.
  - `affaan-m/everything-claude-code@security-review`: checklist estático de 10 domínios, exemplos só
    TypeScript/Next.js/Supabase, *"doesn't teach it to check context first"*, e tem uma seção Solana
    que denuncia origem em um único projeto. → **hoje o repo é [`affaan-m/ECC`](https://github.com/affaan-m/ECC)**.
  - `sergiodxa/agent-skills@owasp-security-check`: bem estruturado (20 regras, 5 categorias, 1 arquivo por
    regra), mas *"examples are TypeScript-only, and there's no mechanism for filtering false positives or
    tracing data flow. It's a good reference, just not a methodology."*
  - `alirezarezvani/claude-skills@senior-security`: *"It's not actually a code review skill. It's a security
    engineering toolkit […]. Wrong tool for the job."*
  - `davila7/claude-code-templates@security-review`: *"A copy of the affaan-m skill with two extra
    frontmatter lines. Properly attributed, but adds nothing. Skip."*
  - 🏆 **`getsentry/skills@security-review`** — *"the clear winner, by a wide margin"*: sistema de
    confiança que corta ruído, consciência de falso-positivo, análise de fluxo de dados antes de reportar,
    e *"dozens of supporting reference files"* (verificado: 17 refs de vuln + 2 de linguagem + 1 de infra).

### 3.5 Code review como skill — a crítica mais útil

- **[HN #47262895 — "What to Put in a Claude Code Skill for Reviewing Your Team's Code"](https://news.ycombinator.com/item?id=47262895)** (9 pts, 13 com.):
  - `rgambee`: *"most of these instructions belong in CLAUDE.md instead of or in addition to a specialized
    review skill."*
  - `nbosse`: *"Auto-review on routine PRs produced too much noise. A one-line config change doesn't need a
    12-point review."*
  - `mckennameyer`: *"Aren't vibe PRs way more likely to get abandoned?"*
- **[HN #47649301 — "Crabby – Claude Code skill that reviews code like the Rust compiler"](https://news.ycombinator.com/item?id=47649301)** (6 pts):
  `moropex`: *"I'll give it a shot. I have a pretty massive rust micro services architecture, this could
  be a nice addition."* → a ideia de review com voz de compilador tem tração, mas pouca adoção medida.
- **[HN #49235255 — "Whetstone – 20 Claude Code skills, each distilled from one real failure"](https://news.ycombinator.com/item?id=49235255)** (6 pts, 0 comentários) — interessante a tese (1 skill = 1 falha real), mas **sem validação comunitária**.

### 3.6 anthropics/skills — elogio e crítica direta no issue tracker

- **[Issue #202 — "skill-creator should be updated to best practice"](https://github.com/anthropics/skills/issues/202)** (aberto 02/01/2026 por `oaustegard`):
  - *"The skill-creator skill reads more like developer documentation than an operational skill. It
    explains concepts to humans rather than instructing Claude on execution."*
  - *"The skill is 356 lines—approaching the 500-line ceiling intended for maximum complexity. A meta-skill
    about creating skills shouldn't consume this much context."*
  - *"The context window is a public good"* → deveria ser *"Minimize token usage; challenge each line's
    necessity"* (framing filosófico vs. diretiva imperativa).
  - Nome viola a convenção de gerúndio (`skill-creator` → deveria ser `creating-skills`).
  - ⚠️ **Nota**: o issue diz 356 linhas; o arquivo no `main` hoje tem **485 linhas** — ou seja, **piorou**.
- **[skillproof.dev — "Skill Creator — Claude Skill, Tested (9.6/10)"](https://skillproof.dev/skills/skill-creator)** (testado 26/06/2026, Claude Code) — elogio forte de plataforma de teste.
- **[Delv — "Skill Creator Review"](https://delv.tools/skills/skill-creator)** — *"Anthropic's official meta-Skill for authoring other Skills."*
- **[Hwee-Boon Yar — "Using the Skill-Creator Skill to Improve Your Existing Skills"](https://hboon.com/using-the-skill-creator-skill-to-improve-your-existing-skills/)**
  — elogia a atualização que adicionou **evals**: testar a skill contra prompts sintéticos, graduar outputs e comparar versões.
- **[DEV — "I Used Skill Creator v2 to Improve One of My Agent Skills in VS Code"](https://dev.to/debs_obrien/i-used-skill-creator-v2-to-improve-one-of-my-agent-skills-in-vs-code-fhd)**
- **[Medium/All About Claude — "I Tested Anthropic's Skill-Creator Plugin on My Own Skills"](https://medium.com/all-about-claude/i-tested-anthropics-skill-creator-plugin-on-my-own-skills-what-i-found-23ad406b0825)**

### 3.7 Conflito de opinião: skill ≠ checklist

Recorrente nos threads HN: instruções específicas de repo (estilo de código, comandos) pertencem ao
`CLAUDE.md`/`AGENTS.md`; skills valem quando (a) carregam **scripts/dados específicos**, (b) são
**grandes o bastante para não caber no contexto sempre-ligado**, ou (c) codificam uma **metodologia**
(como o sistema de confiança do Sentry ou o "find root cause first" do Superpowers).
Referências: [HN 47262895](https://news.ycombinator.com/item?id=47262895) (`rgambee`),
[HN 49529329](https://news.ycombinator.com/item?id=49529329) (`clickety_clack`).

### 3.8 Reddit / LocalLLaMA `[índice]` — não pude ler o corpo do thread

- [r/LocalLLaMA — "Been using PI Coding Agent with local Qwen3.6 35b… The real game changer was the plan-first skill file"](https://www.reddit.com/r/LocalLLaMA/comments/1stjwg5/been_using_pi_coding_agent_with_local_qwen36_35b/)
- [r/LocalLLaMA — "Agent Skills in 100 lines of Python"](https://www.reddit.com/r/LocalLLaMA/comments/1qdp00e/agent_skills_in_100_lines_of_python/)
- [r/LocalLLaMA — "Can you guys help me understand skills better?"](https://www.reddit.com/r/LocalLLaMA/comments/1q9mlyk/can_you_guys_help_me_understand_skills_better/)
- [runlocal.cc — "Claude shipped 'Agent Skills'. r/LocalLLaMA already converged on the canonical 4"](https://runlocal.cc/blog/canonical-local-llm-skill-library)
  — a tese dos "4 canônicos": **plan-first, test-first, refactor-with-constraint, debug-loop**.

---

## 4. Portabilidade por CLI (validado onde possível)

| CLI | Descoberta de skills | Evidência |
|---|---|---|
| **Claude Code** | `~/.claude/skills/<name>/SKILL.md`, `.claude/skills/` | Padrão de origem do formato `SKILL.md` |
| **OpenCode** | `.opencode/skills/*/SKILL.md`, **e também** `.claude/skills/*/SKILL.md` e `.agents/skills/*/SKILL.md` (anda para cima até o worktree git) | ✅ [docs oficiais `opencode.ai/docs/skills/`](https://opencode.ai/docs/skills/) |
| **Crush** | Padrão aberto Agent Skills; builtin embarcados via `go:embed` | ✅ `gh api repos/charmbracelet/crush/contents/internal/skills/builtin` retornou `crush-config`, `crush-hooks`, `jq` — cada um com `SKILL.md`. Spec: [agentskills.io](https://agentskills.io) |
| **Codex** | `~/.codex/skills/` (via instaladores de terceiros) | ✅ citado no README do `alirezarezvani/claude-skills` (`npx agent-skills-cli add … --agent codex`, `./scripts/codex-install.sh`, `~/.codex/skills/`) |
| **Gemini CLI / Cursor / Aider / Windsurf / Kilo / Augment / Antigravity / Hermes** | `./scripts/install.sh --tool <x>`; Cursor em `.mdc` | ✅ README do `alirezarezvani/claude-skills` + README do `wshobson/agents` (export para Claude Code, Cursor, Codex CLI, OpenCode, Gemini CLI) |

**Consequência prática para o kit:** escreva cada skill como pasta com `SKILL.md` + `references/` +
`scripts/` e instale em **`.agents/skills/`** (lido por OpenCode) e/ou `.claude/skills/`. O
`alirezarezvani/claude-skills` é o único projeto validado que já entrega **mirror trees** para
`.codex/`, `.gemini/`, `.vibe/`, `.hermes/` a partir de uma fonte única, com `scripts/convert.sh`.

---

## 5. TOP 12 — skills de codificação (qualidade real + popularidade)

Ordenado por **qualidade verificada do arquivo + evidência externa**, não por stars do repo.

| # | Skill | Repo | URL | Linhas | Por quê (1 linha) |
|---|---|---|---|---|---|
| 1 | `security-review` | getsentry/skills | https://github.com/getsentry/skills/blob/main/skills/security-review/SKILL.md | 312 + 20 refs | Única review de segurança com sistema de confiança e fluxo de dados; venceu comparação de 5 skills com folga |
| 2 | `code-review-excellence` | wshobson/agents | https://github.com/wshobson/agents/blob/main/plugins/developer-essentials/skills/code-review-excellence/SKILL.md | 529 | Review em 4 fases cronometradas, com checklists de segurança/perf e nitpick jogado no linter |
| 3 | `test-driven-development` | obra/superpowers | https://github.com/obra/superpowers/blob/main/skills/test-driven-development/SKILL.md | 320 | "Se você não viu o teste falhar, não sabe se ele testa o certo" — a regra que mais muda comportamento |
| 4 | `systematic-debugging` | obra/superpowers | https://github.com/obra/superpowers/blob/main/skills/systematic-debugging/SKILL.md | 283 | Proíbe fix no sintoma e obriga achar a causa raiz antes de tocar em código |
| 5 | `verification-before-completion` | obra/superpowers | https://github.com/obra/superpowers/blob/main/skills/verification-before-completion/SKILL.md | 120 | "Evidence before claims" — mata o falso "done" com a menor quantidade de texto |
| 6 | `code-review` (2 eixos) | mattpocock/skills | https://github.com/mattpocock/skills/blob/main/skills/engineering/code-review/SKILL.md | 87 | Standards vs Spec em subagentes paralelos; radicalmente enxuta para o que entrega |
| 7 | `writing-skills` | obra/superpowers | https://github.com/obra/superpowers/blob/main/skills/writing-skills/SKILL.md | 679 | Guia definitivo de autoria de skill — insumo direto do kit do Davi |
| 8 | `skill-creator` | anthropics/skills | https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md | 485 | Oficial, com evals para testar triggering; aceita as críticas do issue #202 (verboso/485 linhas) |
| 9 | `debugging-strategies` | wshobson/agents | https://github.com/wshobson/agents/blob/main/plugins/developer-essentials/skills/debugging-strategies/SKILL.md | 527 | Debug sistemático + profiling agnóstico de stack, o mais completo do gênero |
| 10 | `subagent-driven-development` | obra/superpowers | https://github.com/obra/superpowers/blob/main/skills/subagent-driven-development/SKILL.md | 568 | 1 subagente fresco por tarefa + review por tarefa + review final — o núcleo do Superpowers |
| 11 | `diagnosing-bugs` | mattpocock/skills | https://github.com/mattpocock/skills/blob/main/skills/engineering/diagnosing-bugs/SKILL.md | 138 | Loop de diagnóstico com fase de redação de dados sensíveis, inclui regressão de performance |
| 12 | `pr-review-expert` | alirezarezvani/claude-skills | https://github.com/alirezarezvani/claude-skills/blob/main/engineering/skills/pr-review-expert/SKILL.md | 397 | Review de PR orientado a risco, em repo que já exporta nativamente 13 CLIs |

**Menções honrosas (custo≈0 de contexto, alto valor):** `tdd` (38 linhas, mattpocock), `resolving-merge-conflicts`
(14 linhas), `commit` (62), `code-simplifier` (119), `find-bugs` (75), `skill-security-auditor` (171 — audita
a skill *antes* de instalar, faz sentido em kit portátil), `architecture-decision-records` (441).

> ✅ **Verificação das 12 URLs acima:** os 12 caminhos foram conferidos arquivo-a-arquivo no clone local
> (`test -f` → 12/12 `OK`) e o `default_branch` de todos os 6 repos é `main` (`gh api repos/… --jq .default_branch`),
> então os links `blob/main/...` resolvem.

**Não recomendadas:** `davila7/claude-code-templates@security-review` (cópia sem valor agregado),
`sickn33/*@security-review` (cópia verbatim em bundle — install count ≠ qualidade),
`alirezarezvani@senior-security` para *review de código* (é toolkit de threat modeling),
`steipete/agent-rules` (arquivado), `wshobson` plugins `comprehensive-review`/`code-refactoring`/`git-pr-workflows`
(**não são skills**, só commands+agents).

---

## 6. Lições práticas

1. **Popularidade de bundle engana.** `sickn33` (46k stars, 2115 skills) e `davila7` (30k stars) distribuem
   cópias. Ranqueie por arquivo, não por repo — foi o que a comparação do TimOnWeb mostrou.
2. **Skill boa é metodologia, não checklist.** As 3 mais bem avaliadas daqui (Sentry `security-review`,
   Superpowers `systematic-debugging`, Sentry `code-review`) mudam *como o agente raciocina*; as criticadas
   (affaan-m `security-review`, Matt Pocock no HN) são bancos de instruções estáticas.
3. **Enxuto ganha.** `tdd` (38) e `resolving-merge-conflicts` (14) do mattpocock carregam mais sinal por
   token que arquivos de 500+ linhas — e o issue #202 do `anthropics/skills` ataca exatamente o excesso.
4. **Cuidado com o instalador.** O próprio HN chamou o instalador Codex/OpenCode do Superpowers de
   *"curl|bash com LLM no meio"*. Para kit portátil: `git clone --depth 1` e cópia auditada, nunca pipe direto.
5. **Escreva para `.agents/skills/`.** É o denominador comum validado entre OpenCode, Crush e Claude Code.

---

## 7. Pendências / NAO_VALIDADO (honestidade de escopo)

| Item | Status |
|---|---|
| Corpo de qualquer thread do Reddit | ⛔ **BLOQUEADO (403)** — só título/URL/trecho via índice de busca |
| `affaan-m/ECC` — linha exata de `github-ops`, `verification-loop` e demais skills fora do filtro inicial | `NAO_VALIDADO` |
| `alirezarezvani` — `tdd-guide`, `senior-security`, `legacy-modernizer`, `code-reviewer` (linhas) | `NAO_VALIDADO` (arquivo existe, contagem não coletada) |
| `sergiodxa/agent-skills@owasp-security-check` — caminho + linhas | `NAO_VALIDADO` (repo validado, conteúdo não clonado) |
| `aidankinzett/claude-git-pr-skill`, `anthroos/claude-code-review-skill`, `Dilaz/security-review-skill` | `NAO_VALIDADO` (repos validados; conteúdo não inspecionado) |
| `getsentry/skills` — 993 stars é baixo para a qualidade; re-checar antes de descartar por popularidade | ⚠️ |
| Star counts de `obra/superpowers` (287k), `anthropics/skills` (176k), `mattpocock/skills` (263k), `affaan-m/ECC` (260k) | ⚠️ retornados literalmente por `gh api`; parecem inflados, re-checar |
| `karanb192/awesome-claude-skills` ("50+ verified skills") | ❌ clone retornou **0 `SKILL.md`** — é lista, não pacote |
| `VoltAgent/awesome-claude-code-subagents` | ❌ clone retornou **0 `SKILL.md`** — formato `agents/*.md` |

---

*Arquivo gerado por pesquisa direta (gh api + git clone + wc -l + HN Algolia + curl) em 2026-09-16.
Nenhum nome de skill, caminho ou contagem de linhas deste documento foi escrito de memória.*
