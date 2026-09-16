# Catálogo de skills

129 skills, todas verificadas contra a spec Agent Skills (`python3 tools/validate-skills.py`).

**core** = instalada por padrão (`install.sh`). **extra** = só com `--tier all` (mantém a lista inicial curta: o Codex corta descrições quando há muitas skills).

## Codificação — 36 skills

Disciplina de engenharia: teste antes do código, causa raiz antes do patch, review antes do commit, verificação antes de dizer 'pronto'.

| skill | tier | linhas | origem | licença | o que faz |
|---|---|---|---|---|---|
| `code-review-excellence` | core | 530 | wshobson/agents | MIT | Master effective code review practices to provide constructive feedback, catch bugs early, and foster knowledge sharing while maintaining team mora... |
| `codebase-onboarding` | core | 235 | affaan-m/ECC | MIT | Analyze an unfamiliar codebase and generate a structured onboarding guide with architecture map, key entry points, conventions, and a starter CLAUD... |
| `coding-standards` | core | 552 | affaan-m/ECC | MIT | Baseline cross-project coding conventions for naming, readability, immutability, and code-quality review. Use detailed frontend or backend skills f... |
| `git-advanced-workflows` | core | 199 | wshobson/agents | MIT | Master advanced Git workflows including rebasing, cherry-picking, bisect, worktrees, and reflog to maintain clean history and recover from any situ... |
| `requesting-code-review` | core | 96 | obra/superpowers | MIT | Use when completing tasks, implementing major features, or before merging to verify work meets requirements |
| `search-first` | core | 184 | affaan-m/ECC | MIT | Research-before-coding workflow. Search for existing tools, libraries, and patterns before writing custom code. Invokes the researcher agent. |
| `security-review` | core | 505 | affaan-m/ECC | MIT | Use this skill when adding authentication, handling user input, working with secrets, creating API endpoints, or implementing payment/sensitive fea... |
| `systematic-debugging` | core | 284 | obra/superpowers | MIT | Use when encountering any bug, test failure, or unexpected behavior, before proposing fixes |
| `test-driven-development` | core | 321 | obra/superpowers | MIT | Use when implementing any feature or bugfix, before writing implementation code |
| `verification-before-completion` | core | 121 | obra/superpowers | MIT | Use when about to claim work is complete, fixed, or passing, before committing or creating PRs - requires running verification commands and confirm... |
| `ai-regression-testing` | extra | 387 | affaan-m/ECC | MIT | Regression testing strategies for AI-assisted development. Sandbox-mode API testing without database dependencies, automated bug-check workflows, a... |
| `api-design` | extra | 525 | affaan-m/ECC | MIT | REST API design patterns including resource naming, status codes, pagination, filtering, error responses, versioning, and rate limiting for product... |
| `api-design-principles` | extra | 111 | wshobson/agents | MIT | Master REST and GraphQL API design principles to build intuitive, scalable, and maintainable APIs that delight developers. Use when designing new A... |
| `benchmark` | extra | 96 | affaan-m/ECC | MIT | Use this skill to measure performance baselines, detect regressions before/after PRs, and compare stack alternatives. |
| `codebase-inspection` | extra | 117 | local (skill pessoal, herdada de ~/.hermes/skills) | MIT | Inspect codebases w/ pygount: LOC, languages, ratios. |
| `contract-first` | extra | 288 | affaan-m/ECC | MIT | Use when multiple consumers and providers must evolve an API or event schema without field drift, integration surprises, or one side silently redef... |
| `database-migrations` | extra | 431 | affaan-m/ECC | MIT | Database migration best practices for schema changes, data migrations, rollbacks, and zero-downtime deployments across PostgreSQL, MySQL, and commo... |
| `dead-code-elimination` | extra | 71 | local (skill pessoal, herdada de ~/.hermes/skills) | MIT | Use when pruning dead code, CSS or i18n keys from a repo. |
| `debugging-strategies` | extra | 528 | wshobson/agents | MIT | Master systematic debugging techniques, profiling tools, and root cause analysis to efficiently track down bugs across any codebase or technology s... |
| `dependency-upgrade` | extra | 369 | wshobson/agents | MIT | Manage major dependency version upgrades with compatibility analysis, staged rollout, and comprehensive testing. Use when upgrading framework versi... |
| `deployment-patterns` | extra | 429 | affaan-m/ECC | MIT | Deployment workflows, CI/CD pipeline patterns, Docker containerization, health checks, rollback strategies, and production readiness checklists for... |
| `docker-patterns` | extra | 521 | affaan-m/ECC | MIT | Docker and Docker Compose patterns for local development, hardened CLI installer harnesses, container security, networking, volumes, and multi-serv... |
| `electron-app-maintenance` | extra | 74 | local (skill pessoal, herdada de ~/.hermes/skills) | MIT | Use when building or debugging an Electron desktop app. |
| `executing-plans` | extra | 65 | obra/superpowers | MIT | Use when you have a written implementation plan to execute in a separate session with review checkpoints |
| `finishing-a-development-branch` | extra | 226 | obra/superpowers | MIT | Use when implementation is complete, all tests pass, and you need to decide how to integrate the work |
| `git-history-rewrite` | extra | 191 | local (skill pessoal, herdada de ~/.hermes/skills) | MIT | Use when rewriting git history (messages, authors). |
| `github-ops` | extra | 163 | affaan-m/ECC | MIT | GitHub repository operations, automation, and management. Issue triage, PR management, CI/CD operations, release management, and security monitorin... |
| `monorepo-management` | extra | 218 | wshobson/agents | MIT | Master monorepo management with Turborepo, Nx, and pnpm workspaces to build efficient, scalable multi-package repositories with optimized builds an... |
| `node-inspect-debugger` | extra | 320 | local (skill pessoal, herdada de ~/.hermes/skills) | MIT | Debug Node.js via --inspect + Chrome DevTools Protocol CLI. |
| `openapi-spec-generation` | extra | 67 | wshobson/agents | MIT | Generate and maintain OpenAPI 3.1 specifications from code, design-first specs, and validation patterns. Use when creating API documentation, gener... |
| `python-debugpy` | extra | 374 | local (skill pessoal, herdada de ~/.hermes/skills) | MIT | Debug Python: pdb REPL + debugpy remote (DAP). |
| `python-performance-optimization` | extra | 101 | wshobson/agents | MIT | Profile and optimize Python code using cProfile, memory profilers, and performance best practices. Use when debugging slow Python code, optimizing ... |
| `python-project-structure` | extra | 253 | wshobson/agents | MIT | Python project organization, module architecture, and public API design. Use when setting up new projects, organizing modules, defining public inte... |
| `receiving-code-review` | extra | 206 | obra/superpowers | MIT | Use when receiving code review feedback, before implementing suggestions, especially if feedback seems unclear or technically questionable - requir... |
| `simplify-code` | extra | 271 | local (skill pessoal, herdada de ~/.hermes/skills) | MIT | Parallel 4-agent cleanup of recent code changes. |
| `sql-optimization-patterns` | extra | 215 | wshobson/agents | MIT | Master SQL query optimization, indexing strategies, and EXPLAIN analysis to dramatically improve database performance and eliminate slow queries. U... |

## Pensamento e planejamento — 27 skills

Pensar antes de escrever: destilar a intenção, escrever plano executável, registrar decisão, pesquisar o que já existe.

| skill | tier | linhas | origem | licença | o que faz |
|---|---|---|---|---|---|
| `architecture-decision-records` | core | 442 | wshobson/agents | MIT | Write and maintain Architecture Decision Records (ADRs) following best practices for technical decision documentation. Use when documenting signifi... |
| `blueprint` | core | 107 | affaan-m/ECC | MIT | >- |
| `bmad-forge-idea` | core | 108 | bmad-code-org/BMAD-METHOD | MIT | Test a half-formed idea in a questioning conversation, with different personas probing its weak points, until the user can act on it or drop it wit... |
| `bmad-spec` | core | 161 | bmad-code-org/BMAD-METHOD | MIT | Condense any input — an idea, brief, PRD, transcript, or mixed notes — into a short spec: SPEC.md plus supporting files that downstream skills buil... |
| `brainstorming` | core | 251 | obra/superpowers | MIT | You MUST use this before any creative work - creating features, building components, adding functionality, or modifying behavior. Explores user int... |
| `discernment-nudge` | core | 210 | anthropics/skills | Apache-2.0 | After you give a substantive answer or draft that the user may act on — advice or recommendations, drafted artifacts such as goals, plans, pitches,... |
| `skill-creator` | core | 486 | anthropics/skills | Apache-2.0 | Create new skills, modify and improve existing skills, and measure skill performance. Use when users want to create a skill from scratch, edit, or ... |
| `spike` | core | 198 | local (skill pessoal, herdada de ~/.hermes/skills) | MIT | Throwaway experiments to validate an idea before build. |
| `writing-plans` | core | 172 | obra/superpowers | MIT | Use when you have a spec or requirements for a multi-step task, before touching code |
| `agent-self-evaluation` | extra | 183 | affaan-m/ECC | MIT | Use after completing any non-trivial task. The agent self-rates its output on 5 axes — accuracy, completeness, clarity, actionability, conciseness ... |
| `before-you-build` | extra | 51 | wshobson/agents | MIT | Pre-build product and feature risk review for founders, product managers, and AI-assisted builders. Use this skill when the user is about to build ... |
| `blocked-page-recovery` | extra | 138 | local (skill pessoal, herdada de ~/.hermes/skills) | MIT | Use when a fetch fails: 403/429, paywall, WAF, bot wall. |
| `bmad-advanced-elicitation` | extra | 65 | bmad-code-org/BMAD-METHOD | MIT | Push the LLM to reconsider, refine, and improve its recent output. Use when user asks for deeper critique or mentions a known deeper critique metho... |
| `bmad-brainstorming` | extra | 81 | bmad-code-org/BMAD-METHOD | MIT | Facilitate a brainstorming session using diverse creative techniques. Use when the user says 'help me brainstorm' or 'help me ideate |
| `bmad-prfaq` | extra | 134 | bmad-code-org/BMAD-METHOD | MIT | Test a product concept with Amazon's Working Backwards method: write the press release for the finished product first, then answer hard customer an... |
| `context-budget` | extra | 137 | affaan-m/ECC | MIT | Audits Claude Code context window consumption across agents, skills, MCP servers, and rules. Identifies bloat, redundant components, and produces p... |
| `deep-research` | extra | 171 | affaan-m/ECC | MIT | Multi-source deep research using firecrawl and exa MCPs. Searches the web, synthesizes findings, and delivers cited reports with source attribution... |
| `dev-team` | extra | 204 | affaan-m/ECC | MIT | Simulate a collaborative dev team session where multiple role-based personas (PM, Architect, Developer, QA) respond to the same problem together in... |
| `grounded-citations` | extra | 254 | local (skill pessoal, herdada de ~/.hermes/skills) | MIT | Ground answers and documents in cited, verifiable sources. |
| `postmortem-writing` | extra | 234 | wshobson/agents | MIT | Write effective blameless postmortems with root cause analysis, timelines, and action items. Use when conducting incident reviews, writing postmort... |
| `prompt-engineering-patterns` | extra | 145 | wshobson/agents | MIT | >- |
| `research-ops` | extra | 114 | affaan-m/ECC | MIT | Evidence-first current-state research workflow for ECC. Use when the user wants fresh facts, comparisons, enrichment, or a recommendation built fro... |
| `scan` | extra | 219 | wshobson/agents | MIT | Scans the codebase to generate project-doc.md and AGENTS.md. Use when bootstrapping a new agent-driven repo, refreshing project documentation after... |
| `strategic-compact` | extra | 157 | affaan-m/ECC | MIT | Suggests manual context compaction at logical intervals to preserve context through task phases rather than arbitrary auto-compaction. Use when a s... |
| `token-budget-advisor` | extra | 135 | affaan-m/ECC | MIT | >- |
| `writing-guidelines` | extra | 40 | vercel-labs/agent-skills | MIT | Review docs/prose for Writing Guidelines compliance. Use when asked to "review my docs", "check writing style", "audit prose", "review docs voice a... |
| `writing-skills` | extra | 680 | obra/superpowers | MIT | Use when creating new skills, editing existing skills, or verifying skills work before deployment |

## Trabalho em grupo (subagentes) — 16 skills

Dividir trabalho entre subagentes com contexto isolado, worktrees paralelos e review por um segundo agente.

| skill | tier | linhas | origem | licença | o que faz |
|---|---|---|---|---|---|
| `dispatching-parallel-agents` | core | 168 | obra/superpowers | MIT | Use when facing 2+ independent tasks that can be worked on without shared state or sequential dependencies |
| `multi-reviewer-patterns` | core | 128 | wshobson/agents | MIT | Coordinate parallel code reviews across multiple quality dimensions with finding deduplication, severity calibration, and consolidated reporting. U... |
| `subagent-driven-development` | core | 569 | obra/superpowers | MIT | Use when executing implementation plans with independent tasks in the current session |
| `task-coordination-strategies` | core | 164 | wshobson/agents | MIT | Decompose complex tasks, design dependency graphs, and coordinate multi-agent work with proper task descriptions and workload balancing. Use this s... |
| `using-git-worktrees` | core | 168 | obra/superpowers | MIT | Use when starting feature work that needs isolation from current workspace or before executing implementation plans - ensures an isolated workspace... |
| `bmad-party-mode` | extra | 61 | bmad-code-org/BMAD-METHOD | MIT | Orchestrates lively group discussions between installed BMAD agents or custom personas, and helps author custom parties. Use when the user requests... |
| `dmux-workflows` | extra | 193 | affaan-m/ECC | MIT | Multi-agent orchestration using dmux (tmux pane manager for AI agents). Patterns for parallel agent workflows across Claude Code, Codex, OpenCode, ... |
| `iterative-retrieval` | extra | 213 | affaan-m/ECC | MIT | Pattern for progressively refining context retrieval to solve the subagent context problem. Use when a subagent lacks the context it needs and retr... |
| `on-call-handoff-patterns` | extra | 71 | wshobson/agents | MIT | Master on-call shift handoffs with context transfer, escalation procedures, and documentation. Use this skill when transitioning on-call responsibi... |
| `parallel-execution-optimizer` | extra | 75 | affaan-m/ECC | MIT | Use when the user wants a task done much faster through parallel work, concurrent agents, batched tool calls, isolated worktrees, or many independe... |
| `parallel-feature-development` | extra | 175 | wshobson/agents | MIT | Coordinate parallel feature development with file ownership strategies, conflict avoidance rules, and integration patterns for multi-agent implemen... |
| `review-agent-setup` | extra | 171 | wshobson/agents | MIT | Configure human-in-the-loop gating for AI agent review actions in Claude Code. Use when setting up a project where an agent may post PR reviews, co... |
| `santa-method` | extra | 308 | affaan-m/ECC | MIT | Multi-agent adversarial verification with convergence loop. Two independent review agents must both pass before output ships. Use when output must ... |
| `team-agent-orchestration` | extra | 112 | affaan-m/ECC | MIT | Run team-based orchestration for agent squads using work items, ownership, agent Kanban, merge gates, and control pane handoffs. Use when coordinat... |
| `team-builder` | extra | 170 | affaan-m/ECC | MIT | Interactive agent picker for composing and dispatching parallel teams. Use when composing and dispatching a parallel team of agents for a task. |
| `unified-memory` | extra | 200 | affaan-m/ECC | MIT | Share durable, inspectable context and handoffs between Claude, Codex, Hermes, Cursor, OpenCode, and other agents through the local ECC Memory Vaul... |

## Frontend e UI — 27 skills

Padrões de UI, acessibilidade, motion e teste visual/e2e — para não entregar tela que 'funciona' e parece amadora.

| skill | tier | linhas | origem | licença | o que faz |
|---|---|---|---|---|---|
| `accessibility` | core | 148 | affaan-m/ECC | MIT | Design, implement, and audit inclusive digital products using WCAG 2.2 Level AA. Use when building or auditing UI that must meet WCAG 2.2 Level AA,... |
| `e2e-testing` | core | 328 | affaan-m/ECC | MIT | Playwright E2E testing patterns, Page Object Model, configuration, CI/CD integration, artifact management, and flaky test strategies. Use when writ... |
| `frontend-design` | core | 72 | anthropics/skills | Apache-2.0 | Guidance for distinctive, intentional visual design when building new UI or reshaping an existing one. Helps with aesthetic direction, typography, ... |
| `make-interfaces-feel-better` | core | 153 | affaan-m/ECC | MIT | Apply concrete design-engineering details that make interfaces feel polished. Use when reviewing or improving UI spacing, typography, borders, shad... |
| `vercel-react-best-practices` | core | 150 | vercel-labs/agent-skills | MIT | React and Next.js performance optimization guidelines from Vercel Engineering. This skill should be used when writing, reviewing, or refactoring Re... |
| `accessibility-compliance` | extra | 52 | wshobson/agents | MIT | Implement WCAG 2.2 compliant interfaces with mobile accessibility, inclusive design patterns, and assistive technology support. Use when auditing a... |
| `browser-qa` | extra | 106 | affaan-m/ECC | MIT | Use this skill to automate visual testing and UI interaction verification using browser automation after deploying features. |
| `click-path-audit` | extra | 246 | affaan-m/ECC | MIT | Trace every user-facing button/touchpoint through its full state change sequence to find bugs where functions individually work but cancel each oth... |
| `design-system` | extra | 84 | affaan-m/ECC | MIT | Use this skill to generate or audit design systems, check visual consistency, and review PRs that touch styling. Use when generating or auditing a ... |
| `dogfood` | extra | 165 | local (skill pessoal, herdada de ~/.hermes/skills) | MIT | Exploratory QA of web apps: find bugs, evidence, reports. |
| `frontend-design-direction` | extra | 94 | affaan-m/ECC | MIT | Set an ECC-specific frontend design direction for production UI work. Use when building or improving websites, dashboards, applications, components... |
| `frontend-patterns` | extra | 658 | affaan-m/ECC | MIT | Frontend development patterns for React, Next.js, state management, performance optimization, and UI best practices. Use when building or reviewing... |
| `motion-patterns` | extra | 436 | affaan-m/ECC | MIT | Production-ready animation patterns for React / Next.js — button, modal, toast, stagger, page transitions, exit animations, scroll, and layout — bu... |
| `nextjs-app-router-patterns` | extra | 115 | wshobson/agents | MIT | Master Next.js 14+ App Router with Server Components, streaming, parallel routes, and advanced data fetching. Use when building Next.js application... |
| `react-modernization` | extra | 329 | wshobson/agents | MIT | Upgrade React applications to latest versions, migrate from class components to hooks, and adopt concurrent features. Use when modernizing React co... |
| `react-performance` | extra | 576 | affaan-m/ECC | MIT | React and Next.js performance optimization patterns adapted from Vercel Engineering's React Best Practices (https://github.com/vercel-labs/agent-sk... |
| `tailwind-design-system` | extra | 187 | wshobson/agents | MIT | Build scalable design systems with Tailwind CSS v4, design tokens, component libraries, and responsive patterns. Use when creating component librar... |
| `vercel-composition-patterns` | extra | 90 | vercel-labs/agent-skills | MIT | React composition patterns that scale. Use when refactoring components with |
| `vercel-react-view-transitions` | extra | 333 | vercel-labs/agent-skills | MIT | Guide for implementing smooth, native-feeling animations using React's View Transition API (`<ViewTransition>` component, `addTransitionType`, and ... |
| `visual-design-foundations` | extra | 319 | wshobson/agents | MIT | Apply typography, color theory, spacing systems, and iconography principles to create cohesive visual designs. Use when establishing design tokens,... |
| `visual-edit-precision` | extra | 54 | wshobson/agents | MIT | >- |
| `vite-patterns` | extra | 451 | affaan-m/ECC | MIT | Vite build tool patterns including config, plugins, HMR, env variables, proxy setup, SSR, library mode, dependency pre-bundling, and build optimiza... |
| `vue-patterns` | extra | 472 | affaan-m/ECC | MIT | Vue.js 3 Composition API patterns, component architecture, reactivity best practices, Pinia state management, Vue Router navigation, and Nuxt SSR p... |
| `web-artifacts-builder` | extra | 74 | anthropics/skills | Apache-2.0 | Suite of tools for creating elaborate, multi-component claude.ai HTML artifacts using modern frontend web technologies (React, Tailwind CSS, shadcn... |
| `web-component-design` | extra | 272 | wshobson/agents | MIT | Master React, Vue, and Svelte component patterns including CSS-in-JS, composition strategies, and reusable component architecture. Use when buildin... |
| `web-design-guidelines` | extra | 40 | vercel-labs/agent-skills | MIT | Review UI code for Web Interface Guidelines compliance. Use when asked to "review my UI", "check accessibility", "audit design", "review UX", or "c... |
| `webapp-testing` | extra | 96 | anthropics/skills | Apache-2.0 | Toolkit for interacting with and testing local web applications using Playwright. Supports verifying frontend functionality, debugging UI behavior,... |

## Orquestração de agentes — 23 skills

Loop autônomo, gates de avaliação, harness e MCP: como o agente avalia a si mesmo em vez de só rodar.

| skill | tier | linhas | origem | licença | o que faz |
|---|---|---|---|---|---|
| `autonomous-loops` | core | 612 | affaan-m/ECC | MIT | Patterns and architectures for autonomous Claude Code loops — from simple sequential pipelines to RFC-driven multi-agent DAG systems. Retained for ... |
| `eval-harness` | core | 306 | affaan-m/ECC | MIT | Formal evaluation framework for Claude Code sessions implementing eval-driven development (EDD) principles. Use when a Claude Code workflow needs a... |
| `loop-design-check` | core | 144 | affaan-m/ECC | MIT | Design a goal-oriented agent loop, and review it for the ways loops go wrong — spinning and burning tokens, Goodhart-gaming the verifier, or runnin... |
| `mcp-builder` | core | 237 | anthropics/skills | Apache-2.0 | Guide for creating high-quality MCP (Model Context Protocol) servers that enable LLMs to interact with external services through well-designed tool... |
| `agent-architecture-audit` | extra | 258 | affaan-m/ECC | MIT | Full-stack diagnostic for agent and LLM applications. Audits the 12-layer agent stack for wrapper regression, memory pollution, tool discipline fai... |
| `agent-harness-construction` | extra | 75 | affaan-m/ECC | MIT | Design and optimize AI agent action spaces, tool definitions, and observation formatting for higher completion rates. Use when defining or revising... |
| `agentic-os` | extra | 389 | affaan-m/ECC | MIT | Build persistent multi-agent operating systems on Claude Code. Covers kernel architecture, specialist agents, slash commands, file-based memory, sc... |
| `autonomous-agent-harness` | extra | 272 | affaan-m/ECC | MIT | Transform Claude Code into a fully autonomous agent system with persistent memory, scheduled operations, computer use, and task queuing. Replaces s... |
| `claude-code` | extra | 746 | local (skill pessoal, herdada de ~/.hermes/skills) | MIT | Delegate coding to Claude Code CLI (features, PRs). |
| `claude-devfleet` | extra | 113 | affaan-m/ECC | MIT | Orchestrate multi-agent coding tasks via Claude DevFleet — plan projects, dispatch parallel agents in isolated worktrees, monitor progress, and rea... |
| `codex` | extra | 152 | local (skill pessoal, herdada de ~/.hermes/skills) | MIT | Delegate coding to OpenAI Codex CLI (features, PRs). |
| `continuous-agent-loop` | extra | 47 | affaan-m/ECC | MIT | Patterns for continuous autonomous agent loops with quality gates, evals, and recovery controls. Use when running an agent loop that must self-chec... |
| `cost-aware-llm-pipeline` | extra | 189 | affaan-m/ECC | MIT | Cost optimization patterns for LLM API usage — model routing by task complexity, budget tracking, retry logic, and prompt caching. Use when LLM spe... |
| `dynamic-workflow-mode` | extra | 125 | affaan-m/ECC | MIT | Design task-local harnesses, eval gates, and reusable skill extraction for Claude dynamic workflow mode and other adaptive agent harnesses. Use whe... |
| `gan-style-harness` | extra | 280 | affaan-m/ECC | MIT | GAN-inspired Generator-Evaluator agent harness for building high-quality applications autonomously. Based on Anthropic's March 2026 harness design ... |
| `herdr-orchestrator` | extra | 793 | local (skill pessoal, herdada de ~/.hermes/skills) | MIT | Orchestrate parallel agent teams in Herdr with review. |
| `langchain-architecture` | extra | 274 | wshobson/agents | MIT | Design LLM applications using LangChain 1.x and LangGraph for agents, memory, and tool integration. Use when building LangChain applications, imple... |
| `mcp-server-patterns` | extra | 71 | affaan-m/ECC | MIT | Build MCP servers with Node/TypeScript SDK — tools, resources, prompts, Zod validation, stdio vs Streamable HTTP. Use Context7 or official MCP docs... |
| `opencode` | extra | 220 | local (skill pessoal, herdada de ~/.hermes/skills) | MIT | Delegate coding to OpenCode CLI (features, PR review). |
| `orch-pipeline` | extra | 122 | affaan-m/ECC | MIT | Shared orchestration engine for the orch-* skill family. Defines the gated Research-Plan-TDD-Review-Commit pipeline, the size classifier, the agent... |
| `plan-orchestrate` | extra | 264 | affaan-m/ECC | MIT | Read a plan document, decompose it into steps, design a per-step agent chain from the ECC catalogue, and emit ready-to-paste /orchestrate custom pr... |
| `ralphinho-rfc-pipeline` | extra | 69 | affaan-m/ECC | MIT | RFC-driven multi-agent DAG execution pattern with quality gates, merge queues, and work unit orchestration. Use when running RFC-driven multi-agent... |
| `worktrunk` | extra | 167 | max-sixty/worktrunk | MIT OR Apache-2.0 | Guidance for Worktrunk (the `wt` CLI) — git worktree management, hooks, and config. Load when working out which worktree a `wt` command will act on... |

## Skills que dependem de ferramenta externa

Estas não são autossuficientes: sem o binário/serviço, a instrução continua
legível, mas o agente não consegue executar o fluxo.

| Skill | Precisa de |
|---|---|
| `worktrunk` | CLI `wt` (worktrunk) instalado |
| `browser-qa`, `e2e-testing`, `dogfood`, `webapp-testing` | navegador / Playwright |
| `mcp-builder`, `mcp-server-patterns` | SDK do MCP (`@modelcontextprotocol/sdk` ou Python) |
| `claude-code`, `codex`, `opencode` | a CLI correspondente instalada |
| `herdr-orchestrator` | Herdr (e os workers em panes) |
| `vercel-react-best-practices`, `vercel-react-view-transitions` | projeto React 18+/Next |
| `deep-research` | MCPs `firecrawl` e `exa` |

O resto das skills do catálogo não precisa de nada além de shell e leitura de arquivo.
