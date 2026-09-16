# 02 — Skills de Pensamento & Trabalho em Grupo com Subagentes (agentes CLI)

> Pesquisa para Davi · gerado em 2026-09-16 · destino: `~/Documents/projects/Skills/research/`
> Escopo: skills de *thinking/reasoning/planning* e skills/padrões de *multi-agent orchestration* para agentes CLI (Claude Code, OpenCode, Codex, Gemini CLI, Pi).

---

## 0. Metodologia e status de validação

Tudo abaixo foi conferido com terminal, não com memória de modelo. Comandos usados:

```bash
gh api repos/<owner>/<repo> --jq '.stargazers_count'      # stars/forks/pushed_at
git clone --depth 1 https://github.com/<owner>/<repo> /tmp/skr/<repo>
find <repo> -name "SKILL.md"                              # caminhos reais
curl -s -o /dev/null -w '%{http_code}' -L <url-do-arquivo>  # confirma que o arquivo existe
```

**Ambiente:** `/tmp/skr/` (clones rasos, 2026-09-16). `gh` autenticado como `imperat-on`.

### Legenda
| Marca | Significado |
|---|---|
| ✅ VALIDADO | repo clonado, arquivo lido no disco, URL do arquivo retornou HTTP 200 |
| ⚠️ PARCIAL | repo/URL confirmado (gh api 200) mas **não clonei** o conteúdo |
| ❌ NAO_VALIDADO | não consegui confirmar neste ambiente (ver motivo) |

### Contagem de estrelas (medida em 2026-09-16, `gh api`)
| Repo | Stars | Forks | Último push |
|---|---:|---:|---|
| `sst/opencode` | 207.901 | — | 2026-09-16 |
| `obra/superpowers` | 287.594 | 25.723 | 2026-09-14 |
| `anthropics/skills` | 176.699 | 20.921 | 2026-09-10 |
| `anthropics/claude-code` | 145.416 | — | 2026-09-16 |
| `github/spec-kit` | 137.349 | — | 2026-09-16 |
| `openai/codex` | 124.729 | — | 2026-09-16 |
| `modelcontextprotocol/servers` | 90.388 | 11.640 | 2026-09-03 |
| `ruvnet/claude-flow` | 72.626 | — | 2026-09-16 |
| `hesreallyhim/awesome-claude-code` | 54.171 | — | — |
| `bmad-code-org/BMAD-METHOD` | 53.104 | — | 2026-09-16 |
| `wshobson/agents` | 39.728 | 4.232 | 2026-09-14 |
| `humanlayer/humanlayer` | 11.552 | — | 2026-06-19 |
| `disler/claude-code-hooks-multi-agent-observability` | 1.537 | — | — |
| `disler/super-simple-software-factory` | 860 | — | — |
| `disler/infinite-agentic-loop` | 617 | — | — |
| `disler/the-library` | 421 | — | — |
| `disler/agent-sandbox-skill` | 386 | — | — |

> ⚠️ Correção de premissa da tarefa: **`kmgb/awesome-claude-code` não existe** — `gh api` retorna `HTTP 404: Not Found`. A lista real e popular é **`hesreallyhim/awesome-claude-code`** (54.171⭐, confirmado). Marcado como NAO_VALIDADO o repo `kmgb`.

### Total de skills verificadas em disco
| Repo | SKILL.md encontrados (`find -name SKILL.md \| wc -l`) |
|---|---:|
| `obra/superpowers` | 14 |
| `anthropics/skills` | 19 (+1 em `template/`) |
| `wshobson/agents` | 183 |
| `bmad-code-org/BMAD-METHOD` (`skills/`) | 29 |

---

# PARTE 1 — SKILLS DE PENSAMENTO

## 1.1 Brainstorming / Ideation

### 1. `superpowers:brainstorming` — ✅ VALIDADO
- **URL:** https://github.com/obra/superpowers/blob/main/skills/brainstorming/SKILL.md
- **Caminho no disco:** `/tmp/skr/superpowers/skills/brainstorming/SKILL.md` (250 linhas)
- **O que resolve:** transforma ideia vaga em design+spec antes de escrever código. Classifica o pedido em **três trilhas** (`Spike` / `Bounded` / spec completo) e exige gate de aprovação humana.
- **Mecanismo central (trecho real):**
  > `<HARD-GATE> Do NOT invoke any implementation skill, write any code, scaffold any project, or take any implementation action until you have told your human partner what you intend and they have approved it. ... the ceremony scales with the task; the approval gate never does.`
- **Por que importa:** o gate é *invariante* (não escala com o tamanho da tarefa) mas a *cerimônia* escala. Isso evita o modo de falha clássico de brainstorming: burocracia de spec para mudar um flag.
- **Exemplo concreto de uso:** usuário diz "quero adicionar suporte a OAuth". A skill classifica como `Bounded`, faz 2-3 perguntas que importam, apresenta design curto *no chat* e só depois libera implementação. Se fosse "dá pra usar CRDT pra isso?" → classifica `Spike`, 2-3 frases, testa barato, reporta recomendação e joga o protótipo fora.

### 2. `bmad-brainstorming` + Brainstorming Coach — ✅ VALIDADO
- **URL (coach):** https://github.com/bmad-code-org/BMAD-METHOD/blob/main/web-bundles/brainstorming-coach/SKILL.md
- **O que resolve:** facilitação de sessão de brainstorm onde **o agente não gera ideias** — só enquadra, pergunta e organiza. Puxa de 60 técnicas em `brain-methods.csv` (11 categorias: collaborative, creative, structured, deep, wild, theatrical, introspective_delight, biomimetic, cultural, quantum, meta).
- **Três modos de falha nomeados (trecho real):**
  - *"The 2-and-take-over trap"* — usuário dá 2-3 ideias, o agente "ajuda" dando exemplos, e mata a sessão. A jogada certa é a pergunta que destrava 5 ideias novas **do usuário**.
  - *"Seeded questions are illegal"* — `"What if you tried a subscription model?"` embute a resposta; `"What pricing structures have you not considered?"` abre o espaço.
  - *"Quantity unlocks quality"* — meta ~100 ideias (short ~30, deep ~150) **antes** de qualquer organização: "the breakthroughs live past idea 20".
- **Anti-cluster:** a cada 10 ideias, audita temas e **anuncia pivô de domínio** — "LLMs cluster semantically; the pivot is the antidote".
- **Exemplo concreto:** pedir brainstorm de nomes/posicionamento para um produto. A skill abre Canvas, força ~30+ ideias cruas, força pivô de domínio a cada 10, e só então agrupa em Mermaid (mind-map de temas, quadrante de priorização).

### 3. `bmad-party-mode` (round-table multi-persona) — ✅ VALIDADO
- **URL:** https://github.com/bmad-code-org/BMAD-METHOD/blob/main/skills/bmad-party-mode/SKILL.md
- **O que resolve:** mesa-redonda onde agentes/personas "conversam entre si e com o usuário como pessoas distintas", para perspectiva múltipla / focus group de IA. Orquestrador resolve roster via `uv run scripts/resolve_party.py`, com memória por-party em `.memlog.md`.
- **Exemplo concreto:** `/party` → entram PM, Arquiteto, UX e Dev; cada um critica a proposta pela sua lente; usuário assiste e intervém; memória persiste entre sessões.

## 1.2 Plan-first / Spec-Driven Development

### 4. `superpowers:writing-plans` — ✅ VALIDADO
- **URL:** https://github.com/obra/superpowers/blob/main/skills/writing-plans/SKILL.md
- **Caminho:** `/tmp/skr/superpowers/skills/writing-plans/SKILL.md` (171 linhas)
- **O que resolve:** escreve plano de implementação assumindo que **quem executa tem zero contexto do repo e gosto duvidoso**.
- **Trecho real:**
  > "Assume they are a skilled developer, but know almost nothing about our toolset or problem domain. Assume they don't know good test design very well."
- **Mecanismo:** *File Structure* primeiro (decisões de decomposição ficam travadas aqui) → *Task Right-Sizing* → tarefas bite-sized com TDD e commits frequentes. Destino padrão: `docs/superpowers/plans/YYYY-MM-DD-<feature>.md`.
- **Detalhe bom:** "A task is the smallest unit that carries its own test cycle and is worth a fresh reviewer's gate" — o critério de granularidade é *a revisão*, não o tamanho do diff.
- **Exemplo concreto:** após um brainstorming aprovado, gera plano em 6 tarefas; cada tarefa diz arquivos exatos, o teste a escrever primeiro, e o comando de verificação.

### 5. `github/spec-kit` — Spec-Driven Development (prompts `/speckit.*`) — ✅ VALIDADO
- **URL repo:** https://github.com/github/spec-kit (137.349⭐)
- **Prompts reais (validados 200):**
  - `templates/commands/constitution.md` — https://github.com/github/spec-kit/blob/main/templates/commands/constitution.md
  - `templates/commands/clarify.md` — https://github.com/github/spec-kit/blob/main/templates/commands/clarify.md
  - `templates/commands/analyze.md` — https://github.com/github/spec-kit/blob/main/templates/commands/analyze.md
  - `templates/commands/checklist.md`, `plan.md`, `specify.md`, `tasks.md`, `implement.md`, `converge.md`, `taskstoissues.md`
- **Templates:** `templates/spec-template.md`, `plan-template.md`, `tasks-template.md`, `constitution-template.md`, `checklist-template.md`
- **O que resolve:** fluxo spec-first com portões de qualidade. Três prompts merecem destaque como *skills de pensamento*:
  - **`/clarify`** — "Identify underspecified areas in the current feature spec by asking up to 5 highly targeted clarification questions and encoding answers back into the spec". O limite de **5 perguntas** é o ponto: Socratic questioning com orçamento.
  - **`/analyze`** — "Perform a non-destructive cross-artifact consistency and quality analysis across spec.md, plan.md, and tasks.md after task generation". Detective de inconsistência entre documentos.
  - **`/constitution`** — princípios não-negociáveis do projeto, escritos *antes* do código.
- **Mecanismo extra:** `handoffs:` no frontmatter (ex.: `clarify` declara handoff → `speckit.plan`), hooks por extensão via `.specify/extensions.yml` (`hooks.before_clarify`, `hooks.before_analyze`).
- **Exemplo concreto:** `/speckit.clarify` num spec de upload de arquivos devolve ≤5 perguntas ("limite de tamanho? quem pode deletar? o que acontece em timeout?") e **edita o spec.md** com as respostas. Depois `/speckit.analyze` checa se plan.md e tasks.md ainda batem com o spec.

### 6. `superpowers:executing-plans` — ✅ VALIDADO
- **URL:** https://github.com/obra/superpowers/blob/main/skills/executing-plans/SKILL.md (64 linhas)
- **O que resolve:** executa plano já escrito em sessão separada, com checkpoints de revisão. Passo 1 é literalmente "Review critically — identify any questions or concerns about the plan. If concerns: raise them with your human partner **before starting**".
- **Nota de roteamento real:** a própria skill diz que se o harness tem subagentes, use `subagent-driven-development` em vez dela.
- **Exemplo concreto:** sessão nova, `executing-plans` carrega `docs/superpowers/plans/2026-09-16-oauth.md`, cria todos por tarefa, executa com verificação por tarefa, e ao final delega obrigatoriamente para `finishing-a-development-branch`.

### 7. "Plan mode" nativo (OpenCode `plan` agent) — ✅ VALIDADO
- **URL:** https://opencode.ai/docs/agents/
- **O que resolve:** modo de planejamento *no harness*, não em prompt. `plan` é "A restricted agent designed for planning and analysis... By default, all of the following are set to **ask**: file edits (writes, patches, edits), bash (all commands)".
- **Exemplo concreto:** no OpenCode, `Tab` alterna para `plan`; o agente analisa e propõe sem conseguir escrever. Só depois troca para `build`.

## 1.3 Sequential Thinking (reasoning estruturado)

### 8. Sequential Thinking MCP Server — ✅ VALIDADO
- **URL:** https://github.com/modelcontextprotocol/servers/blob/main/src/sequentialthinking/README.md
- **Caminho:** `/tmp/skr/modelcontextprotocol_servers/src/sequentialthinking/` (`index.ts`, `lib.ts`, `README.md`, `Dockerfile`, testes)
- **Repo:** `modelcontextprotocol/servers` (90.388⭐); publicado no npm como `@modelcontextprotocol/server-sequential-thinking`
- **O que resolve:** quebra problema em passos revisáveis, com **revisão e ramificação explícitas**.
- **Schema real da tool `sequential_thinking`:** `thought`, `nextThoughtNeeded`, `thoughtNumber`, `totalThoughts`, `isRevision`, `revisesThought`, `branchFromThought`, `branchId`, `needsMoreThoughts`.
- **O diferencial é `isRevision`/`branchFromThought`** — não é "pense passo a passo" (CoT simples); é *poder marcar o passo 7 como revisão do passo 3* e *abrir ramo a partir do passo 5*.
- **Exemplo concreto (do próprio README):** `"Plan a database migration from PostgreSQL 14 to 16, list risks, and **revise the plan if downtime exceeds 5 minutes**."` — o "revise se…" é o que aciona `isRevision`.
- **Como saber que está funcionando:** o inspector/host deve mostrar **múltiplas** chamadas a `sequential_thinking` com `thoughtNumber` crescente, não uma resposta one-shot.
- **Status de ceticismo:** a própria comunidade questiona o ganho — ver §3.4.

## 1.4 ADR / Architecture Decision Records

### 9. `architecture-decision-records` (wshobson/agents) — ✅ VALIDADO
- **URL:** https://github.com/wshobson/agents/blob/main/plugins/documentation-generation/skills/architecture-decision-records/SKILL.md
- **Caminho:** `/tmp/skr/wshobson_agents/plugins/documentation-generation/skills/architecture-decision-records/SKILL.md`
- **O que resolve:** "Write and maintain Architecture Decision Records (ADRs) following best practices... Use when documenting significant technical decisions, reviewing past architectural choices, or establishing decision processes."
- **Cobre:** o que é um ADR, trade-offs de design, onboarding, revisão de decisões históricas, processo de decisão.
- **Exemplo concreto:** `/code-review` ou pedido "documenta por que escolhemos Postgres em vez de DynamoDB" → gera ADR com contexto, decisão, alternativas rejeitadas e consequências.
- **Relacionadas no mesmo repo (validadas em disco):** `architecture-patterns`, `c4-architecture`, `backend-development/skills/architecture-patterns`.

## 1.5 Pre-mortem / Risco / Tech-debt / Postmortem

### 10. `before-you-build` (pre-mortem de produto) — ✅ VALIDADO
- **URL:** https://github.com/wshobson/agents/blob/main/plugins/before-you-build/skills/before-you-build/SKILL.md
- **Caminho:** `/tmp/skr/wshobson_agents/plugins/before-you-build/skills/before-you-build/SKILL.md` (+ `references/risk-checklist.md`)
- **O que resolve:** **pre-mortem compacto** antes da implementação. 7 eixos de risco: **Demand, Positioning, Monetization, Retention, Trust, Distribution, Feature adoption.**
- **Trecho real que define o tom:** "The goal is not to block building; it is to identify the highest-risk assumption, the smallest validation step, and the build scope that should be delayed until evidence improves."
- **Formato de saída fixo (5 itens):** 1. Risk verdict (Low/Med/High + 1 frase) · 2. Main assumption · 3. Evidence to find first · 4. Do next · 5. **Delay** (o que *não* construir ainda).
- **Anti-alucinação embutido:** "If facts are missing, name the missing evidence instead of inventing market claims."
- **Exemplo concreto:** "quero construir um SaaS de agendamento" → verdict *high risk* porque a assunção quebradiça é retenção (agendamento é commoditizado); menor validação = landing page + 10 conversas; **delay** = não construir o app mobile ainda.

### 11. `postmortem-writing` (blameless) — ✅ VALIDADO
- **URL:** https://github.com/wshobson/agents/blob/main/plugins/incident-response/skills/postmortem-writing/SKILL.md
- **Caminho:** `/tmp/skr/wshobson_agents/plugins/incident-response/skills/postmortem-writing/SKILL.md`
- **O que resolve:** postmortem sem culpa, com root cause, timeline, e action items. A tabela real:
  | Blame-Focused | Blameless |
  |---|---|
  | "Who caused this?" | "What conditions allowed this?" |
  | "Someone made a mistake" | "The system allowed this mistake" |
  | Punish individuals | Improve systems |
  | Hide information | Share learnings |
- **Exemplo concreto:** pós-incidente de deploy, gera timeline com timestamps, distingue *trigger* de *contributing factors*, e converte cada causa em action item com dono.

### 12. `ai-debt-detector` (dívida técnica *específica de IA*) — ✅ VALIDADO
- **URL:** https://github.com/wshobson/agents/blob/main/plugins/skill-forge-essentials/skills/ai-debt-detector/SKILL.md
- **Caminho:** `/tmp/skr/wshobson_agents/plugins/skill-forge-essentials/skills/ai-debt-detector/SKILL.md`
- **O que resolve:** caça os padrões de dívida que **agentes de IA produzem e humanos não**. Trecho real:
  > "AI agents generate code that passes the happy path but hides debt: missing error handling, orphaned resources, ignored failure modes, hallucinated packages, silent architectural drift. This skill forces a targeted audit for the exact patterns AI agents get wrong."
- **Gatilho incomum e útil:** "when the agent claims done but hidden debt may exist" — auditoria que reage à *declaração de conclusão* do próprio agente.
- **Exemplo concreto:** após gerar 300 linhas de um módulo, roda o detector → ele acha `import` de pacote inexistente (alucinação), `try/finally` faltando num handle de arquivo, e `except: pass` engolindo erro.

### 13. Análise de risco estruturada (STRIDE / attack tree) — ✅ VALIDADO (paths)
- `plugins/security-compliance/skills/stride-analysis-patterns/SKILL.md`
- `plugins/security-compliance/skills/attack-tree-construction/SKILL.md`
- `plugins/security-compliance/skills/threat-mitigation-mapping/SKILL.md`
- **O que resolve:** transformar "e a segurança?" em taxonomia executável (STRIDE: Spoofing, Tampering, Repudiation, Information disclosure, DoS, Elevation of privilege) e árvores de ataque.
- **Exemplo concreto:** modelar um endpoint de login → STRIDE gera 6 linhas de ameaça, cada uma mapeada para mitigação.
- **Nota:** são de segurança, mas o *padrão de raciocínio* (taxonomia fixa + mapeamento para ação) é o mesmo do ADR/pre-mortem.

## 1.6 Socratic questioning / Clarify / Analyze

Cobertos por **`/speckit.clarify`** e **`/speckit.analyze`** (§1.4 item 5) e por `superpowers:brainstorming` (§1.1 item 1). O padrão comum que vale roubar:
- **perguntas com orçamento** (≤5 no clarify) — força priorização;
- **respostas voltam para o artefato** ("encoding answers back into the spec.md"), não para o chat;
- **análise cross-artifact** (spec ↔ plan ↔ tasks) — a inconsistência entre documentos é o bug mais barato de achar.

## 1.7 Discernment / Rubber-duck / Anti-overreliance

### 14. `discernment-nudge` (anthropics/skills) — ✅ VALIDADO
- **URL:** https://github.com/anthropics/skills/blob/main/skills/discernment-nudge/SKILL.md
- **Caminho:** `/tmp/skr/anthropics_skills/skills/discernment-nudge/SKILL.md`
- **O que resolve:** o oposto de "agente confiante". Depois de uma resposta substantiva em que o usuário **pode agir** (conselho, plano, proposta, estimativa, claim factual, argumento multi-passo), anexa **2-3 perguntas curtas de follow-up**, cada uma amarrada a algo específico do que acabou de ser produzido.
- **Três hábitos que ele *modela* (não prega):**
  - **Checking facts** — que claims específicos valem verificação, e contra o quê?
  - **Questioning reasoning** — onde a lógica deu um passo que o usuário talvez queira ver justificado?
  - **Noticing missing context** — o que a resposta teve que assumir porque o usuário não disse?
- **Limites explícitos (bom design):** **no máximo uma vez por conversa**; pula em how-to trivial, lookup simples, formatação/conversão, código que o usuário vai rodar, escrita criativa, e quando o usuário **já** pediu revisão.
- **Exemplo concreto:** usuário pede "vale a pena migrar pra Postgres?" → resposta normal + *"Você mencionou 50k req/dia — esse número é pico ou média? Sua assunção de que o time atual consegue manter Postgres particionado veio de onde?"*

### 15. `superpowers:receiving-code-review` — ✅ VALIDADO
- **URL:** https://github.com/obra/superpowers/blob/main/skills/receiving-code-review/SKILL.md
- **O que resolve:** o lado *recebedor* da revisão — como responder a feedback sem aceitar cegamente nem descartar. É a versão "rubber-duck disciplinado" do loop de revisão.
- **PAR:** `requesting-code-review` (§2.4).

## 1.8 Systems thinking / Context engineering

### 16. Anthropic — "Effective context engineering for AI agents" — ✅ VALIDADO (conteúdo lido)
- **URL:** https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents (publicado 2025-09-29)
- **Conceito real e citável — "context rot":**
  > "as the number of tokens in the context window increases, the model's ability to [recall/attend]..."
- **Por que é *a* skill de pensamento estruturante:** a tese é que engenharia de contexto substitui engenharia de prompt — "the engineering problem at hand is optimizing the utility of those tokens against the inherent constraints of LLMs". Justifica *por que* isolamento de contexto (§2.1) funciona.
- **Exemplo concreto de uso:** antes de mandar 40 arquivos para o agente, decidir o que entra no contexto por *curadoria* e não por "tudo que pode ser relevante" — a janela degrada com volume.

### 17. `superpowers:systematic-debugging` — ✅ VALIDADO (metadados; skill detalhada em `01-coding-skills.md`)
- **URL:** https://github.com/obra/superpowers/blob/main/skills/systematic-debugging/SKILL.md
- **O que resolve:** processo de root cause em 4 fases (o README lista: "4-phase root cause process, includes root-cause-tracing, defense-in-depth, condition-based-waiting techniques").
- **Nota:** pertence ao irmão `01-coding-skills.md` — não duplico aqui.

---

# PARTE 2 — SKILLS / PADRÕES DE SUBAGENTES E COLABORAÇÃO

## 2.1 Isolamento de contexto (o princípio-raiz)

### 18. `superpowers:dispatching-parallel-agents` — ✅ VALIDADO
- **URL:** https://github.com/obra/superpowers/blob/main/skills/dispatching-parallel-agents/SKILL.md (167 linhas)
- **O que resolve:** delegar N problemas independentes para N agentes com contexto **construído do zero**.
- **O princípio (aparece literalmente em várias skills, é a doutrina):**
  > "You delegate tasks to specialized agents with isolated context. By precisely crafting their instructions and context, you ensure they stay focused... **They should never inherit your session's context or history** — you construct exactly what they need. This also preserves your own context for coordination work."
- **Árvore de decisão (graphviz `dot` real):** múltiplas falhas? → são independentes? → dá pra paralelizar? Se **não** independentes → 1 agente só; se **sim** mas com estado compartilhado → sequencial.
- **Detalhe operacional decisivo:** *"Issue all three subagent dispatches in the same response — they run in parallel... Multiple dispatch calls in one response = parallel execution. One per response = sequential."*
- **Padrão de prompt por agente:** escopo específico (1 arquivo/subsistema) + goal claro + constraints ("don't change other code") + output esperado (resumo do que achou/corrigiu).
- **Exemplo concreto (do SKILL.md):**
  ```
  Subagent (general-purpose): "Fix agent-tool-abort.test.ts failures"
  Subagent (general-purpose): "Fix batch-completion-behavior.test.ts failures"
  Subagent (general-purpose): "Fix tool-approval-race-conditions.test.ts failures"
  # All three run concurrently.
  ```
- **Quando NÃO usar (explícito):** falhas relacionadas (consertar uma conserta as outras), necessidade de entender estado global, ou agentes que interferem entre si.

### 19. `subagent-driven-development` — ✅ VALIDADO (master class)
- **URL:** https://github.com/obra/superpowers/blob/main/skills/subagent-driven-development/SKILL.md (**568 linhas** — a maior e mais detalhada)
- **O que resolve:** executar um plano de implementação com **um implementador novo por tarefa + revisão por tarefa + revisão ampla final**.
- **Fórmula real:** *"Fresh subagent per task + task review (spec + quality) + broad final review = high quality, fast iteration"*
- **Loop por tarefa (do graphviz do arquivo):**
  dispatch implementer → implementa/testa/commita/auto-revisa → **task reviewer** (spec compliance + code quality) → conflito com o texto do plano? → *rule on the conflict, ledger the ruling* → rodada de fix (R≤3: retoma o implementer; **R≥4: implementer novo, modelo mais capaz**) → re-review escopada → se R=5, "breaker trips" → adjudica cada achado → achado load-bearing? → park no ledger com ruling.
- **Regra mais contraintuitiva e mais valiosa — "Rulings, not stalls":**
  > "A running plan does not wait on a human. Conflicts, ambiguities, plan defects, a cap you would have asked to exceed — **decide them**. ... Record every decision in the ledger as `Ruling: <what you decided> — <why> — <what it costs if wrong>`, and keep going. A wrong ruling costs rework your human partner can see and undo; a session parked on a question costs their whole day and buys nothing."
- **As 4 (e só 4) paradas legítimas:** operação irreversível/destrutiva · ação sensível de segurança · efeito fora do worktree que a norma manda perguntar (merge, push em branch compartilhada, publish) · plano tão quebrado que todo caminho é chute.
- **Anti-“deixa eu confirmar”:** "Do not pause to check in... 'Should I continue?' prompts and progress summaries waste their time."
- **Escala o modelo com a dificuldade:** R≥4 troca por "fresh implementer, more capable model".
- **Exemplo concreto:** plano de 6 tarefas → 6 implementadores frescos, 6 revisões de tarefa, 1 revisão final; zero interrupções ao humano; ledger com todas as rulings.

## 2.2 Delegação / Task decomposition

### 20. `task-coordination-strategies` — ✅ VALIDADO
- **URL:** https://github.com/wshobson/agents/blob/main/plugins/agent-teams/skills/task-coordination-strategies/SKILL.md
- **Caminho:** `/tmp/skr/wshobson_agents/plugins/agent-teams/skills/task-coordination-strategies/SKILL.md` (+ `references/task-decomposition.md`, `references/dependency-graphs.md`)
- **O que resolve:** decompor trabalho em unidades paralelizáveis e desenhar **grafos de dependência**.
- **Mecânica real:** campos `blockedBy`/`blocks` (grafo de tarefas), estratégias de decomposição ("By Layer"), critical path, workload balancing.
- **Exemplo concreto:** feature full-stack → decompõe em `schema` → `[api, ui]` (bloqueadas por schema) → `[e2e-tests]` (bloqueada por api+ui); `blockedBy` impede que o agente de UI comece antes do contrato da API existir.

### 21. `parallel-feature-development` — ✅ VALIDADO
- **URL:** https://github.com/wshobson/agents/blob/main/plugins/agent-teams/skills/parallel-feature-development/SKILL.md
- **O que resolve:** o problema que mata paralelismo — **conflito de arquivo**. Solução: *file ownership*.
- **Técnica real (ownership por diretório):**
  ```
  implementer-1: src/components/auth/
  implementer-2: src/api/auth/
  implementer-3: tests/auth/
  ```
- **Também cobre:** interface contracts (implementadores constroem contra a API um do outro antes de estarem prontas), vertical slice **vs** horizontal layer, `references/merge-strategies.md`, `references/file-ownership.md`.
- **Exemplo concreto:** 3 implementadores em auth (frontend/backend/testes) com donos exclusivos de path → zero merge conflict; contratos de interface escritos primeiro.

### 22. `agent-sandbox-skill` (disler) — ⚠️ PARCIAL
- **URL:** https://github.com/disler/agent-sandbox-skill (386⭐)
- **Descrição:** "An agent skill for managing isolated execution environments"
- **O que resolve:** gestão de ambientes isolados para agentes executarem — o pré-requisito físico para paralelismo seguro.
- **Status:** stars/descrição confirmados via `gh api`; **não clonei** o conteúdo. NAO_VALIDADO o caminho exato do SKILL.md.

## 2.3 Planner / Executor / Critic

### 23. `superpowers:requesting-code-review` (revisor como agente separado) — ✅ VALIDADO
- **URL:** https://github.com/obra/superpowers/blob/main/skills/requesting-code-review/SKILL.md
- **O que resolve:** *review-by-separate-agent*. "Dispatch a code reviewer subagent to catch issues before they cascade. **The reviewer gets precisely crafted context for evaluation — never your session's history.**"
- **Gatilhos mandatórios:** após **cada tarefa** em subagent-driven development · após feature grande · **antes de merge na main**. Opcionais: quando travado, antes de refactor (baseline), após bug complexo.
- **Mecânica:** pega SHAs (`BASE_SHA=$(git rev-parse HEAD~1)`, `HEAD_SHA=$(git rev-parse HEAD)`) e passa o intervalo — o revisor lê o *diff*, não o transcript.
- **Exemplo concreto:** `git rev-parse HEAD~1` vs `HEAD` → revisor recebe só o diff + critérios de aceite; devolve achados com severidade; autor decide quais endereçar.

### 24. `multi-reviewer-patterns` (crítico multi-dimensional paralelo) — ✅ VALIDADO
- **URL:** https://github.com/wshobson/agents/blob/main/plugins/agent-teams/skills/multi-reviewer-patterns/SKILL.md
- **Caminho:** `/tmp/skr/wshobson_agents/plugins/agent-teams/skills/multi-reviewer-patterns/SKILL.md` (+ `references/review-dimensions.md`)
- **O que resolve:** revisão paralela em **dimensões de qualidade**, com **deduplicação de achados**, **calibração de severidade** e relatório consolidado.
- **Por que a deduplicação é o ponto:** N revisores geram o mesmo achado N vezes; sem consolidação o autor recebe ruído. Skill trata "finding deduplication" e "severity calibration" como problemas explícitos.
- **Dimensões reais usadas nos presets:** security, performance, architecture (padrão); e no time de segurança: OWASP/vulns, auth/access control, dependencies/supply chain, secrets/configuration.
- **Exemplo concreto:** PR aberto → 3 revisores em paralelo (segurança, performance, arquitetura) → 14 achados brutos → deduplicados para 9, severidade calibrada igual, 1 relatório.

### 25. `review-agent-governance` — política formal para o agente revisor — ✅ VALIDADO (estrutura)
- **Caminho:** `/tmp/skr/wshobson_agents/plugins/review-agent-governance/`
- **O que resolve:** governança do revisor via **políticas Cedar** (`policies/review-agent-governance.cedar`, `.cedarschema`), hooks de assinatura (`hooks/sign.sh`, `evaluate.sh`, `hooks.json`), comandos `approve-review.md` / `list-pending.md`, skill `skills/review-agent-setup/SKILL.md`, e testes (`test/run-tests.sh`, fixtures).
- **Por que é distinto:** não é "peça ao modelo para revisar bem" — é enforcement: o revisor só age conforme política, e as decisões são assinadas/auditáveis.
- **Exemplo concreto:** PR de IA só entra com review assinado por revisor distinto; política nega auto-aprovação.

## 2.4 Git worktrees para paralelismo

### 26. `superpowers:using-git-worktrees` — ✅ VALIDADO
- **URL:** https://github.com/obra/superpowers/blob/main/skills/using-git-worktrees/SKILL.md (167 linhas)
- **O que resolve:** workspace isolado por sessão. Princípio: *"Detect existing isolation first. Then use native tools. Then fall back to git. **Never fight the harness.**"*
- **Step 0 — detecção (código real):**
  ```bash
  GIT_DIR=$(cd "$(git rev-parse --git-dir)" && pwd -P)
  GIT_COMMON=$(cd "$(git rev-parse --git-common-dir)" && pwd -P)
  BRANCH=$(git branch --show-current)
  ```
  Se `GIT_DIR != GIT_COMMON` (e não é submódulo) → **já está** num worktree, não crie outro.
- **Submodule guard (armadilha real):** `git rev-parse --show-superproject-working-tree` — porque `GIT_DIR != GIT_COMMON` também é verdade dentro de submódulo.
- **Exemplo concreto:** iniciar feature → detecta, cria worktree no branch próprio, trabalha isolado; o branch principal nunca é tocado.

### 27. Claude Code — worktrees nativos (`--worktree`) — ✅ VALIDADO (docs oficiais lidas)
- **URL:** https://docs.claude.com/en/docs/claude-code/worktrees
- **O que resolve:** isolamento de sessão *no harness*. `claude --worktree feature-auth` (ou `-w`) cria worktree em `.claude/worktrees/<name>/` no branch `worktree-<name>`.
- **Detalhes operacionais reais:** nomes gerados tipo `bright-running-fox` se omitido; `.worktreeinclude` leva arquivos gitignored (ex.: `.env`) para cada worktree novo; recomendação de adicionar `.claude/worktrees/` ao `.gitignore`; seção própria **"Isolate subagents with worktrees"**; tool `EnterWorktree` permite o agente trocar de worktree mid-sessão (com prompt de permissão se o path estiver fora de `.claude/worktrees/`); suporta **non-git VCS** via hooks.
- **Exemplo concreto:** terminal A `claude -w feature-auth` constrói feature; terminal B `claude -w fix-bug` corrige bug — edições nunca colidem porque são diretórios/branches distintos.

## 2.5 Orchestrator patterns

### 28. Claude Code — **Agent Teams** (orquestração oficial) — ✅ VALIDADO (docs oficiais lidas)
- **URL:** https://docs.claude.com/en/docs/claude-code/agent-teams
- **Estado real (importante):** **experimental, desabilitado por padrão.** Habilita com `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` no `settings.json`/env. Sem a variável, nenhum time é criado.
- **Arquitetura:** uma sessão é **team lead**; teammates rodam em contextos próprios e **conversam diretamente entre si**; há **task list compartilhada** com claim de trabalho; o usuário pode falar com qualquer teammate sem passar pelo lead.
- **Comparação oficial subagents vs agent teams:**
  | | Subagents | Agent teams |
  |---|---|---|
  | Contexto | próprio; resultado volta ao caller | próprio; **totalmente independentes** |
  | Comunicação | retorna ao caller | **teammates se mandam mensagens direto** |
  | Coordenação | main agent gerencia tudo | auto-coordenação + task list compartilhada |
  | Melhor para | tarefa focada | exploração paralela ampla |
- **Casos de uso que a doc considera mais fortes:** research & review (investigar aspectos diferentes e **desafiar achados uns dos outros**); módulos/features novos; **debug com hipóteses concorrentes**; coordenação cross-layer (frontend/backend/testes).
- **Custo declarado oficialmente (crítica da própria Anthropic):** *"Agent teams add coordination overhead and use significantly more tokens than a single session. They work best when teammates can operate independently. For sequential tasks, same-file edits, or work with many dependencies, a single session or subagents are more effective."*
- **Limitações conhecidas declaradas:** session resumption, task coordination e shutdown behavior.
- **Boas práticas na doc:** dar contexto suficiente aos teammates, escolher tamanho de time adequado, dimensionar tarefas, **esperar** os teammates terminarem, começar com research/review, **evitar conflito de arquivo**, monitorar e steer.
- **Exemplo concreto:** "investigar com hipóteses concorrentes" — 3 teammates testam 3 teorias de bug em paralelo e convergem.

### 29. `team-composition-patterns` — dimensionamento do time — ✅ VALIDADO
- **URL:** https://github.com/wshobson/agents/blob/main/plugins/agent-teams/skills/team-composition-patterns/SKILL.md
- **Caminho:** `/tmp/skr/wshobson_agents/plugins/agent-teams/skills/team-composition-patterns/SKILL.md` (+ `references/preset-teams.md`, `references/agent-type-selection.md`)
- **Heurística de tamanho (tabela real):**
  | Complexidade | Tamanho | Quando |
  |---|---:|---|
  | Simple | 1-2 | review de 1 dimensão, bug isolado, feature pequena |
  | Moderate | 2-3 | mudanças multi-arquivo, 2-3 preocupações |
  | Complex | 3-4 | preocupações cross-cutting, feature grande, debug profundo |
  | Very Complex | 4-5 | features full-stack, reviews abrangentes, problemas sistêmicos |
- **Regra de ouro:** *"Start with the smallest team that covers all required dimensions. Adding teammates increases coordination overhead."*
- **Presets reais:** Review Team (3× `team-reviewer`: security/performance/architecture) · Debug Team (3× `team-debugger`, 3 hipóteses concorrentes) · Feature Team (1 lead + 2 implementers) · Fullstack Team (1 lead + frontend + backend + test) · Research Team (3× `general-purpose`) · Security Team (4× reviewer).
- **Exemplo concreto:** PR médio multi-arquivo → 2-3 revisores, não 5. Tamanho do time é derivado da *cobertura de dimensões*, não do tamanho do diff.

### 30. `team-communication-protocols` — handoffs e protocolo entre agentes — ✅ VALIDADO
- **URL:** https://github.com/wshobson/agents/blob/main/plugins/agent-teams/skills/team-communication-protocols/SKILL.md
- **Caminho:** `/tmp/skr/wshobson_agents/plugins/agent-teams/skills/team-communication-protocols/SKILL.md` (+ `references/messaging-patterns.md`)
- **O que resolve:** como agentes trocam informação sem virar fofoca/loop. Padrões de mensagem, handoff, e propriedade da informação.
- **Exemplo concreto:** implementer termina → publica handoff estruturado (o quê mudou, arquivos, como verificar, o que ficou aberto) → reviewer consome sem precisar do transcript.

### 31. `disler/super-simple-software-factory` (SSSF) — **orquestrador determinístico** — ✅ VALIDADO
- **URL:** https://github.com/disler/super-simple-software-factory/blob/main/.claude/skills/sssf/SKILL.md
- **Caminho:** `/tmp/skr/disler_super-simple-software-factory/.claude/skills/sssf/SKILL.md`
- **Tese (trecho real):**
  > "Reusable combination of **agents plus code**: deterministic Python ADW scripts own sequencing, retries, and acceptance; coding agents work inside bounded phases; typed JSON envelopes carry context between them. Everything streams into SQLite... **Agent proposes, code disposes.**"
- **Padrão-chave:** a *orquestração é código*, não prompt. O LLM não decide a sequência — o script Python decide; o agente só trabalha dentro da fase.
- **ADWs como tabela:** `adw_scout` (engineer → scout, recon read-only) · `adw_simple_sdlc` (plan → build → test → review → document, 3 commits).
- **Regra de contexto disciplinada:** o orquestrador **não** faz o trabalho ("You do no ADW work yourself: never implement, plan, or test in an agent's place — launch the ADW and watch it"), e **não** faz dashboard não-solicitado:
  > "Volunteered state is guessed state... Probing to look prepared is how you end up confidently wrong in your first message."
- **Handoff:** envelopes JSON tipados entre fases; observabilidade em `adws/adw_data/sssf.db` (SQLite WAL — "reads never block writers").
- **Exemplo concreto:** `/sssf run adw_simple_sdlc` → 5 fases sequenciadas por Python, 3 commits, tudo registrado; o agente orquestrador só reporta "phase name, owner, status, error".

### 32. `ruvnet/claude-flow` — swarm/harness multi-agente — ⚠️ PARCIAL
- **URL:** https://github.com/ruvnet/claude-flow
- **Stars:** 72.626 (confirmado via `gh api`); descrição: "🌊 The original agent harness. Deploy intelligent multi-player swarms, coordinate..."
- **O que resolve:** swarms de agentes com coordenação/harness próprio.
- **Status:** **não clonei** — não afirmo caminhos de arquivo. Marcar NAO_VALIDADO qualquer path específico.

### 33. `bmad-code-org/BMAD-METHOD` — time de agentes por papel — ✅ VALIDADO (estrutura)
- **URL:** https://github.com/bmad-code-org/BMAD-METHOD (53.104⭐) · `skills/` com **29** skills
- **Padrão:** agentes por *papel* de time: `bmad-agent-analyst`, `bmad-agent-pm`, `bmad-agent-architect`, `bmad-agent-dev`, `bmad-agent-ux-designer`.
- **Workflow:** `bmad-brainstorming` → `bmad-prd`/`bmad-prfaq`/`bmad-product-brief` → `bmad-architecture` → `bmad-create-epics-and-stories` → `bmad-sprint-planning` → `bmad-build`/`bmad-build-auto` → `bmad-code-review` → `bmad-retrospective`.
- **Skills de pensamento notáveis:** `bmad-advanced-elicitation`, `bmad-correct-course` (mudança de rota), `bmad-party-mode` (§1.1), `bmad-deep-recon`, `bmad-retrospective` (retrospectiva).
- **Exemplo concreto:** rodar o ciclo Analyst → PM (PRD) → Architect → Dev, com `bmad-correct-course` quando o escopo desanda e `bmad-retrospective` no fim.

### 34. `disler/infinite-agentic-loop` — ⚠️ PARCIAL
- **URL:** https://github.com/disler/infinite-agentic-loop (617⭐)
- **Descrição:** "An experimental project demonstrating Infinite Agentic Loop in a two prompt system using Claude" — loop agêntico em dois prompts.
- **Status:** stars/descrição via `gh api`; clonei mas a estrutura é `src/`, `src_group/`, `src_infinite/` — **não há SKILL.md**. Não cito path de skill.

### 35. `disler/the-library` — meta-skill de distribuição — ✅ VALIDADO
- **URL:** https://github.com/disler/the-library/blob/main/SKILL.md
- **Caminho:** `/tmp/skr/disler_the-library/SKILL.md`
- **O que resolve:** distribuição privada de skills/agents/prompts entre agentes, máquinas e **times** (421⭐).
- **Ponto de design elegante:** *"The `library.yaml` is a catalog, not a manifest. Entries define what's available — not what gets installed. You pull specific items on demand with `/library use <name>`."* + "Nothing is fetched until you ask for it." — catálogo lazy vs manifest eager.
- **Exemplo concreto:** `/library add` registra uma skill; `/library use security-audit` puxa só aquele item; o resto do catálogo não custa contexto.

### 36. `disler/claude-code-hooks-multi-agent-observability` — observabilidade — ⚠️ PARCIAL
- **URL:** https://github.com/disler/claude-code-hooks-multi-agent-observability (1.537⭐)
- **Descrição:** "Real-time monitoring for Claude Code agents through simple hook event tracking."
- **O que resolve:** você não pode orquestrar o que não vê. Hooks emitem eventos de agentes; monitor em tempo real.
- **Status:** `gh api` confirmado; não clonei o conteúdo.

## 2.6 Nativos por harness (OpenCode / Codex)

### 37. OpenCode — agents/subagents nativos — ✅ VALIDADO (doc lida)
- **URL:** https://opencode.ai/docs/agents/ · repo `sst/opencode` (207.901⭐, o maior da lista)
- **Dois tipos:** **primary agents** (Build, Plan — `Tab` alterna) e **subagents** (invocados por primary ou por `@mention`).
- **Subagents built-in (reais):** `general` ("Has full tool access... **Use this to run multiple units of work in parallel**") · `explore` ("A fast, read-only agent for exploring codebases. Cannot modify files") · `scout` ("read-only agent for external docs and dependency research... clone a dependency repository into OpenCode's managed cache").
- **Isolamento por permissão:** `Plan` tem file edits e bash em **`ask`** por padrão.
- **Configurável por** JSON ou Markdown, com `description`, `temperature`, `max steps`, `prompt`, `model`, `permissions`, `mode`, `hidden`, `task permissions`.
- **Exemplo concreto:** `@explore` mapeia o repo sem poder editar; `@general` roda N unidades de trabalho em paralelo; `plan` projeta sem escrever; `build` executa.
- **Doc de skills:** https://opencode.ai/docs/skills/ (Agent Skills suportado).

### 38. OpenAI Codex CLI — ⚠️ PARCIAL
- **URL:** https://github.com/openai/codex (124.729⭐)
- **Status:** repo confirmado via `gh api`; **não validei** docs de subagents/paralelismo neste ambiente. Marcar NAO_VALIDADO qualquer afirmação específica sobre recursos de subagente do Codex.

## 2.7 Fundamentos quantitativos (por que multi-agente funciona — e quanto custa)

### 39. Anthropic — "How we built our multi-agent research system" — ✅ VALIDADO (conteúdo lido)
- **URL:** https://www.anthropic.com/engineering/multi-agent-research-system (publicado 2025-06-13)
- **Números reais (a evidência medida que importa):**
  - Lead Claude Opus 4 + subagentes Claude Sonnet 4 **superaram single-agent Opus 4 em 90,2%** na eval interna de research.
  - **Token usage explica 80% da variância** no BrowseComp (com número de tool calls e escolha de modelo como os outros fatores — juntos, os três explicam **95%**).
  - Agentes usam **~4× mais tokens** que chat; **multi-agente ~15× mais tokens** que chat.
- **Conclusão econômica declarada:** *"For economic viability, multi-agent systems require tasks where the value of the task is high enough to pay for the increased performance."*
- **Por que subagentes ajudam — tese de *compressão*:**
  > "The essence of search is compression... Subagents facilitate compression by operating in parallel with their own context windows... Each subagent also provides separation of concerns—distinct tools, prompts, and exploration trajectories—which **reduces path dependency**."
- **Contra-indicação declarada:** domínios que exigem que todos os agentes compartilhem o mesmo contexto, ou com muitas dependências, não se beneficiam.
- **Exemplo concreto (do post):** identificar todos os board members das empresas de TI do S&P 500 — multi-agente decompõe em subagentes e **acha**; single-agent falha com buscas lentas e sequenciais.

---

# PARTE 3 — ONDE FOI ELOGIADO / CRITICADO

## 3.1 Elogios com lastro

| Alvo | Evidência | Fonte |
|---|---|---|
| Multi-agente (arquitetura) | +90,2% sobre single-agent na eval interna; token usage = 80% da variância | ✅ https://www.anthropic.com/engineering/multi-agent-research-system |
| Isolamento de contexto | "context rot": performance degrada com o volume de tokens | ✅ https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents |
| Adoção de `superpowers` | 287.594⭐ / 25.723 forks — o repo de skills mais estrelado do levantamento | ✅ `gh api repos/obra/superpowers` |
| Adoção de `spec-kit` | 137.349⭐ para Spec-Driven Development | ✅ `gh api repos/github/spec-kit` |
| Adoção de `BMAD-METHOD` | 53.104⭐, 29 skills, atualizado 2026-09-16 | ✅ `gh api` + `ls skills/` |

## 3.2 Críticas oficiais (da própria Anthropic, sobre seu produto)

| Crítica | Texto | Fonte |
|---|---|---|
| Agent teams custam caro | "add coordination overhead and use **significantly more tokens**... For sequential tasks, same-file edits, or work with many dependencies, a single session or subagents are more effective." | ✅ https://docs.claude.com/en/docs/claude-code/agent-teams |
| Agent teams são experimentais | "experimental and **disabled by default**... known limitations around session resumption, task coordination, and shutdown behavior." | ✅ mesma URL |
| Multi-agente queima token | "multi-agent systems use about **15× more tokens** than chats" | ✅ blog multi-agent |
| Contexto é finito | "context rot": mais tokens → menos capacidade | ✅ blog context engineering |

## 3.3 Críticas da comunidade — ❌ NAO_VALIDADO
Estes threads foram encontrados por busca web (título e URL reais retornados pelo buscador), mas **não consegui abrir o conteúdo**: `/` e o navegador receberam **HTTP 403 "You've been blocked by network security"** (bot wall do Reddit). Portanto: **trato como NAO_VALIDADO** — cito como existentes, não como lidos.

| Item | URL | Status |
|---|---|---|
| "superpowers skill is very bad - overrated" (r/ClaudeCode) | https://www.reddit.com/r/ClaudeCode/comments/1u6oihk/superpowers_skill_is_very_bad_overrated/ | ❌ 403 |
| "Anyone else not a fan of the superpowers plugin?" (r/ClaudeCode) | https://www.reddit.com/r/ClaudeCode/comments/1rmi6pr/anyone_else_not_a_fan_of_the_superpowers_plugin/ | ❌ 403 |
| "Claude Code's Superpowers plugin actually delivers" (r/ClaudeCode) — contraponto elogioso | https://www.reddit.com/r/ClaudeCode/comments/1r9y2ka/claude_codes_superpowers_plugin_actually_delivers/ | ❌ 403 |
| "Using Claude Code (obra/superpowers) - how do you..." (r/ClaudeAI) | https://www.reddit.com/r/ClaudeAI/comments/1qj1zjg/using_claude_code_obrasuperpowers_how_do_you/ | ❌ 403 |
| "Add critique skill for nine-dimension self-review" (issue #1013, obra/superpowers) | https://github.com/obra/superpowers/issues/1013 | ⚠️ URL real (via busca); não abri |

**Leitura honesta do padrão:** existe polarização real em torno de `superpowers`. A crítica típica é de **overhead de cerimônia** (o gate de brainstorming + planos longos para tarefas pequenas); a defesa típica é que a cerimônia escala por trilha (`Spike`/`Bounded`) e o gate é que protege. **Não li os threads** — não vou resumir o argumento deles além do título.

## 3.4 Críticas ao Sequential Thinking MCP
Encontrados por busca; **não validei os artigos** (⚠️ PARCIAL): títulos indicam ceticismo ativo sobre o ganho real.
- https://docs.bswen.com/blog/2026-03-17-sequential-thinking-ai-reasoning/ — "Does Sequential Thinking Actually Improve AI Agent Reasoning?"
- https://skiln.co/blog/sequential-thinking-mcp-review-2026 — "Sequential Thinking MCP Review 2026"
- https://chatforest.com/reviews/sequential-thinking-mcp-server/ — "When Your Agent Needs to Think Out Loud"
- https://maketocreate.com/sequential-thinking-in-claude-code-a-practical-mcp-guide/ — guia prático

**Nota técnica que sustenta o ceticismo:** o servidor só *estrutura* o raciocínio em texto (`thought` + metadados). Ele não adiciona capacidade de inferência — em modelos com CoT nativo forte, o ganho marginal tende a ser baixo para problemas simples. O valor real está nos campos `isRevision`/`branchFromThought` (revisão e ramificação explícitas), que o CoT linear não expressa.

## 3.5 Ainda não validado (lacunas declaradas)
- ❌ `kmgb/awesome-claude-code` — **HTTP 404, repo não existe**. A lista real é `hesreallyhim/awesome-claude-code` (54.171⭐).
- ❌ Conteúdo de `disler/agent-sandbox-skill`, `disler/claude-code-hooks-multi-agent-observability`, `ruvnet/claude-flow`, `humanlayer/humanlayer` — `gh api` confirmou existência/stars, **não clonei**.
- ❌ Docs de subagents do **OpenAI Codex CLI** — não abertas neste ambiente.
- ❌ `https://claude.com/blog/subagents-in-claude-code` — HTTP 200 e título confirmado ("How and when to use subagents in Claude Code"), mas o corpo é renderizado por JS e **não extraí o texto**.
- ❌ Threads do Reddit — 403 (bot wall).

---

# PARTE 4 — TOP 10: SKILLS DE PENSAMENTO

| # | Skill | URL | Por quê (1 linha) |
|---:|---|---|---|
| 1 | `superpowers:brainstorming` | https://github.com/obra/superpowers/blob/main/skills/brainstorming/SKILL.md | Classifica o pedido em Spike/Bounded/spec e mantém um HARD-GATE de aprovação que **não** escala com o tamanho da tarefa. ✅ |
| 2 | `superpowers:writing-plans` | https://github.com/obra/superpowers/blob/main/skills/writing-plans/SKILL.md | Escreve o plano assumindo executor com zero contexto e gosto duvidoso; granularidade definida pelo *gate de revisão*. ✅ |
| 3 | `spec-kit:/clarify` | https://github.com/github/spec-kit/blob/main/templates/commands/clarify.md | Socratic questioning com **orçamento de ≤5 perguntas** e respostas encodadas de volta no spec. ✅ |
| 4 | `spec-kit:/analyze` | https://github.com/github/spec-kit/blob/main/templates/commands/analyze.md | Checagem de consistência cross-artifact (spec ↔ plan ↔ tasks) — pega a inconsistência mais barata de corrigir. ✅ |
| 5 | `bmad-brainstorming` (+ Brainstorming Coach) | https://github.com/bmad-code-org/BMAD-METHOD/blob/main/skills/bmad-brainstorming/SKILL.md | Agente **não gera ideias**; nomeia os 3 modos de falha ("2-and-take-over", perguntas enviesadas, quantidade antes de qualidade). ✅ |
| 6 | `superpowers:verification-before-completion` | https://github.com/obra/superpowers/blob/main/skills/verification-before-completion/SKILL.md | "NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE" + função-gate de 5 passos; mata o "acho que passou". ✅ |
| 7 | `before-you-build` (pre-mortem) | https://github.com/wshobson/agents/blob/main/plugins/before-you-build/skills/before-you-build/SKILL.md | Pre-mortem de 7 eixos com saída fixa terminando em **Delay** (o que não construir ainda) e proibição de inventar claim de mercado. ✅ |
| 8 | `architecture-decision-records` | https://github.com/wshobson/agents/blob/main/plugins/documentation-generation/skills/architecture-decision-records/SKILL.md | Converte decisão arquitetural em artefato durável com contexto, alternativas rejeitadas e consequências. ✅ |
| 9 | `ai-debt-detector` | https://github.com/wshobson/agents/blob/main/plugins/skill-forge-essentials/skills/ai-debt-detector/SKILL.md | Auditoria dos padrões que **só agentes de IA produzem** (pacote alucinado, recurso órfão, `except: pass`, drift silencioso). ✅ |
| 10 | `discernment-nudge` (anthropics/skills) | https://github.com/anthropics/skills/blob/main/skills/discernment-nudge/SKILL.md | Anti-overreliance: 2-3 perguntas que modelam checar fato / questionar raciocínio / notar contexto faltante — com limites explícitos. ✅ |

**Menções fortes (TOP 11-13):** Sequential Thinking MCP (https://github.com/modelcontextprotocol/servers/blob/main/src/sequentialthinking/README.md — revision/branching explícitos, mas ganho contestado ✅/⚠️) · `postmortem-writing` blameless (https://github.com/wshobson/agents/blob/main/plugins/incident-response/skills/postmortem-writing/SKILL.md ✅) · `bmad-party-mode` (https://github.com/bmad-code-org/BMAD-METHOD/blob/main/skills/bmad-party-mode/SKILL.md ✅).

---

# PARTE 5 — TOP 10: SKILLS / PADRÕES DE SUBAGENTES + COLABORAÇÃO

| # | Skill / Padrão | URL | Por quê (1 linha) |
|---:|---|---|---|
| 1 | `superpowers:subagent-driven-development` | https://github.com/obra/superpowers/blob/main/skills/subagent-driven-development/SKILL.md | 568 linhas: implementador fresco por tarefa + review de tarefa + review final, escalando modelo em R≥4 e **"rulings, not stalls"** com ledger de decisões. ✅ |
| 2 | `superpowers:dispatching-parallel-agents` | https://github.com/obra/superpowers/blob/main/skills/dispatching-parallel-agents/SKILL.md | Doutrina de contexto isolado ("never inherit your session's context") + o detalhe decisivo: dispatches no **mesmo** response = paralelo, um por response = sequencial. ✅ |
| 3 | Claude Code — **Agent Teams** (docs) | https://docs.claude.com/en/docs/claude-code/agent-teams | Orquestração oficial: team lead + task list compartilhada + mensagens diretas entre teammates, com casos de uso e limitações declarados. ✅ |
| 4 | `superpowers:using-git-worktrees` | https://github.com/obra/superpowers/blob/main/skills/using-git-worktrees/SKILL.md | Isolamento de workspace com detecção de worktree existente e **submodule guard** — "never fight the harness". ✅ |
| 5 | Claude Code — worktrees nativos (`--worktree`) | https://docs.claude.com/en/docs/claude-code/worktrees | Paralelismo no harness: `claude -w nome`, `.worktreeinclude`, `EnterWorktree`, isolamento de subagentes. ✅ |
| 6 | `team-composition-patterns` | https://github.com/wshobson/agents/blob/main/plugins/agent-teams/skills/team-composition-patterns/SKILL.md | Heurística de tamanho (1-2 / 2-3 / 3-4 / 4-5) + 6 presets prontos; "comece pelo menor time que cobre as dimensões". ✅ |
| 7 | `task-coordination-strategies` | https://github.com/wshobson/agents/blob/main/plugins/agent-teams/skills/task-coordination-strategies/SKILL.md | Decomposição + grafo de dependências (`blockedBy`/`blocks`) + critical path + rebalanceamento de carga. ✅ |
| 8 | `multi-reviewer-patterns` | https://github.com/wshobson/agents/blob/main/plugins/agent-teams/skills/multi-reviewer-patterns/SKILL.md | Revisão paralela multi-dimensional **com deduplicação de achados e calibração de severidade** — resolve o ruído de N revisores. ✅ |
| 9 | `parallel-feature-development` | https://github.com/wshobson/agents/blob/main/plugins/agent-teams/skills/parallel-feature-development/SKILL.md | Ataca a causa real de conflito em paralelismo: **file ownership** por diretório + interface contracts + vertical slice vs horizontal layer. ✅ |
| 10 | `disler/super-simple-software-factory` (SSSF) | https://github.com/disler/super-simple-software-factory/blob/main/.claude/skills/sssf/SKILL.md | Orquestração **determinística em código** (Python ADW) com agentes confinados a fases — "Agent proposes, code disposes". ✅ |

**Menções fortes (TOP 11-14):** `team-communication-protocols` (handoffs ✅ https://github.com/wshobson/agents/blob/main/plugins/agent-teams/skills/team-communication-protocols/SKILL.md) · `parallel-debugging` (hipóteses concorrentes ✅ https://github.com/wshobson/agents/blob/main/plugins/agent-teams/skills/parallel-debugging/SKILL.md) · OpenCode `@general`/`@explore`/`@scout` (✅ https://opencode.ai/docs/agents/) · `review-agent-governance` (governança Cedar do revisor ✅ path `/tmp/skr/wshobson_agents/plugins/review-agent-governance/`).

---

# PARTE 6 — SÍNTESE: O QUE REALMENTE IMPORTA

Cinco padrões atravessam tudo que foi validado. Se você só levar isto, leve isto:

1. **Contexto é construído, nunca herdado.** Todas as skills fortes repetem: o subagente recebe *exatamente* o que precisa. Motivo medido: "context rot" (performance cai com volume de tokens) e o resultado de +90,2% do sistema multi-agente da Anthropic.
2. **Revisão por agente separado, com escopo cirúrgico.** O revisor recebe o **diff + critérios de aceite**, nunca o transcript. `requesting-code-review` faz isso com dois SHAs de git.
3. **Isolamento físico, não só lógico.** Worktree por sessão/agente. `using-git-worktrees` e `claude -w` atacam a colisão de arquivo na raiz — e `parallel-feature-development` complementa com file ownership.
4. **Decida, não trave.** O padrão mais subestimado ("rulings, not stalls"): ambiguidade num plano incompleto se resolve com uma *ruling* registrada no ledger, não com uma pergunta que para a sessão o dia inteiro.
5. **Paralelismo tem preço explícito.** ~15× tokens vs chat, e a doc oficial do Claude Code diz para preferir sessão única em tarefas sequenciais, no mesmo arquivo, ou com muitas dependências. Paralelize só quando as dimensões são mesmo independentes e o valor da tarefa paga o custo.

**Formato de skill que se repete entre os melhores:** frontmatter com `description` que diz **o quê + quando usar** (é o gatilho de delegação), depois gate/princípio, depois mecanismo, depois *exemplo concreto*, e por fim **quando NÃO usar**. As skills fracas (e as criticadas da §3.3) pulam os dois últimos.
