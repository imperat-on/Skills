# Origens, licenças e créditos

Todos os números abaixo foram medidos nesta máquina em **2026-09-16** (API do GitHub
autenticada, `gh api repos/<repo>` e clones `--depth 1`). Onde eu não consegui medir,
está escrito que não consegui.

## Fontes

| Fonte | Estrelas (2026-09-16) | Licença | Skills usadas | Último push |
|---|---|---|---|---|
| [affaan-m/ECC](https://github.com/affaan-m/ECC) | 260,098 | MIT | 55 | 2026-09-15 |
| [wshobson/agents](https://github.com/wshobson/agents) | 39,729 | MIT | 28 | 2026-09-14 |
| `~/.hermes/skills` (skills pessoais do autor) | — | MIT | 15 | — |
| [obra/superpowers](https://github.com/obra/superpowers) | 287,594 | MIT | 13 | 2026-09-14 |
| [anthropics/skills](https://github.com/anthropics/skills) | 176,699 | Apache-2.0 | 6 | 2026-09-10 |
| [bmad-code-org/BMAD-METHOD](https://github.com/bmad-code-org/BMAD-METHOD) | 53,104 | MIT | 6 | 2026-09-16 |

Total: **123 skills**, 29072 linhas de `SKILL.md`.

Repos que apareceram na pesquisa e **não** viraram dependência (com o motivo) estão em
[REPORT.md](REPORT.md) §4.

## O que foi alterado em cada arquivo

Cada skill é uma cópia fiel do original. A única edição foi **adicionar o campo
`license:`** no frontmatter quando ele não existia (104 arquivos) — metadado exigido
pela spec Agent Skills e que os repositórios de origem declaram só no nível do repo.
Nenhuma linha de instrução foi reescrita, resumida ou traduzida.

Para auditar: `manifest.json` guarda `upstream_path`, `upstream_sha256` (hash do arquivo
no repositório de origem) e `bundled_sha256` (hash do arquivo aqui).

```bash
# conferir um arquivo contra a origem
python3 - <<'EOF'
import json, hashlib, pathlib
for s in json.load(open('manifest.json'))['skills']:
    p = pathlib.Path('skills')/s['category']/s['name']/'SKILL.md'
    h = hashlib.sha256(p.read_bytes()).hexdigest()[:16]
    if h != s['bundled_sha256']: print('DIVERGIU:', s['name'])
print('conferido')
EOF
```

## Crédito por skill

| Skill | Categoria | Tier | Origem | Licença | Linhas |
|---|---|---|---|---|---|
| `code-review-excellence` | coding | core | [wshobson/agents](https://github.com/wshobson/agents) | MIT | 530 |
| `codebase-onboarding` | coding | core | [affaan-m/ECC](https://github.com/affaan-m/ECC) | MIT | 235 |
| `coding-standards` | coding | core | [affaan-m/ECC](https://github.com/affaan-m/ECC) | MIT | 552 |
| `git-advanced-workflows` | coding | core | [wshobson/agents](https://github.com/wshobson/agents) | MIT | 199 |
| `requesting-code-review` | coding | core | [obra/superpowers](https://github.com/obra/superpowers) | MIT | 96 |
| `search-first` | coding | core | [affaan-m/ECC](https://github.com/affaan-m/ECC) | MIT | 184 |
| `security-review` | coding | core | [affaan-m/ECC](https://github.com/affaan-m/ECC) | MIT | 505 |
| `systematic-debugging` | coding | core | [obra/superpowers](https://github.com/obra/superpowers) | MIT | 284 |
| `test-driven-development` | coding | core | [obra/superpowers](https://github.com/obra/superpowers) | MIT | 321 |
| `verification-before-completion` | coding | core | [obra/superpowers](https://github.com/obra/superpowers) | MIT | 121 |
| `ai-regression-testing` | coding | extra | [affaan-m/ECC](https://github.com/affaan-m/ECC) | MIT | 387 |
| `api-design` | coding | extra | [affaan-m/ECC](https://github.com/affaan-m/ECC) | MIT | 525 |
| `api-design-principles` | coding | extra | [wshobson/agents](https://github.com/wshobson/agents) | MIT | 111 |
| `benchmark` | coding | extra | [affaan-m/ECC](https://github.com/affaan-m/ECC) | MIT | 96 |
| `codebase-inspection` | coding | extra | skills pessoais do autor | MIT | 117 |
| `contract-first` | coding | extra | [affaan-m/ECC](https://github.com/affaan-m/ECC) | MIT | 288 |
| `database-migrations` | coding | extra | [affaan-m/ECC](https://github.com/affaan-m/ECC) | MIT | 431 |
| `dead-code-elimination` | coding | extra | skills pessoais do autor | MIT | 71 |
| `debugging-strategies` | coding | extra | [wshobson/agents](https://github.com/wshobson/agents) | MIT | 528 |
| `dependency-upgrade` | coding | extra | [wshobson/agents](https://github.com/wshobson/agents) | MIT | 369 |
| `deployment-patterns` | coding | extra | [affaan-m/ECC](https://github.com/affaan-m/ECC) | MIT | 429 |
| `docker-patterns` | coding | extra | [affaan-m/ECC](https://github.com/affaan-m/ECC) | MIT | 521 |
| `electron-app-maintenance` | coding | extra | skills pessoais do autor | MIT | 74 |
| `executing-plans` | coding | extra | [obra/superpowers](https://github.com/obra/superpowers) | MIT | 65 |
| `finishing-a-development-branch` | coding | extra | [obra/superpowers](https://github.com/obra/superpowers) | MIT | 226 |
| `git-history-rewrite` | coding | extra | skills pessoais do autor | MIT | 191 |
| `github-ops` | coding | extra | [affaan-m/ECC](https://github.com/affaan-m/ECC) | MIT | 163 |
| `monorepo-management` | coding | extra | [wshobson/agents](https://github.com/wshobson/agents) | MIT | 218 |
| `node-inspect-debugger` | coding | extra | skills pessoais do autor | MIT | 320 |
| `openapi-spec-generation` | coding | extra | [wshobson/agents](https://github.com/wshobson/agents) | MIT | 67 |
| `python-debugpy` | coding | extra | skills pessoais do autor | MIT | 374 |
| `python-performance-optimization` | coding | extra | [wshobson/agents](https://github.com/wshobson/agents) | MIT | 101 |
| `python-project-structure` | coding | extra | [wshobson/agents](https://github.com/wshobson/agents) | MIT | 253 |
| `receiving-code-review` | coding | extra | [obra/superpowers](https://github.com/obra/superpowers) | MIT | 206 |
| `simplify-code` | coding | extra | skills pessoais do autor | MIT | 271 |
| `sql-optimization-patterns` | coding | extra | [wshobson/agents](https://github.com/wshobson/agents) | MIT | 215 |
| `accessibility` | frontend | core | [affaan-m/ECC](https://github.com/affaan-m/ECC) | MIT | 148 |
| `e2e-testing` | frontend | core | [affaan-m/ECC](https://github.com/affaan-m/ECC) | MIT | 328 |
| `frontend-design` | frontend | core | [anthropics/skills](https://github.com/anthropics/skills) | Apache-2.0 | 72 |
| `make-interfaces-feel-better` | frontend | core | [affaan-m/ECC](https://github.com/affaan-m/ECC) | MIT | 153 |
| `accessibility-compliance` | frontend | extra | [wshobson/agents](https://github.com/wshobson/agents) | MIT | 52 |
| `browser-qa` | frontend | extra | [affaan-m/ECC](https://github.com/affaan-m/ECC) | MIT | 106 |
| `click-path-audit` | frontend | extra | [affaan-m/ECC](https://github.com/affaan-m/ECC) | MIT | 246 |
| `design-system` | frontend | extra | [affaan-m/ECC](https://github.com/affaan-m/ECC) | MIT | 84 |
| `dogfood` | frontend | extra | skills pessoais do autor | MIT | 165 |
| `frontend-design-direction` | frontend | extra | [affaan-m/ECC](https://github.com/affaan-m/ECC) | MIT | 94 |
| `frontend-patterns` | frontend | extra | [affaan-m/ECC](https://github.com/affaan-m/ECC) | MIT | 658 |
| `motion-patterns` | frontend | extra | [affaan-m/ECC](https://github.com/affaan-m/ECC) | MIT | 436 |
| `nextjs-app-router-patterns` | frontend | extra | [wshobson/agents](https://github.com/wshobson/agents) | MIT | 115 |
| `react-modernization` | frontend | extra | [wshobson/agents](https://github.com/wshobson/agents) | MIT | 329 |
| `react-performance` | frontend | extra | [affaan-m/ECC](https://github.com/affaan-m/ECC) | MIT | 576 |
| `tailwind-design-system` | frontend | extra | [wshobson/agents](https://github.com/wshobson/agents) | MIT | 187 |
| `visual-design-foundations` | frontend | extra | [wshobson/agents](https://github.com/wshobson/agents) | MIT | 319 |
| `visual-edit-precision` | frontend | extra | [wshobson/agents](https://github.com/wshobson/agents) | MIT | 54 |
| `vite-patterns` | frontend | extra | [affaan-m/ECC](https://github.com/affaan-m/ECC) | MIT | 451 |
| `vue-patterns` | frontend | extra | [affaan-m/ECC](https://github.com/affaan-m/ECC) | MIT | 472 |
| `web-artifacts-builder` | frontend | extra | [anthropics/skills](https://github.com/anthropics/skills) | Apache-2.0 | 74 |
| `web-component-design` | frontend | extra | [wshobson/agents](https://github.com/wshobson/agents) | MIT | 272 |
| `webapp-testing` | frontend | extra | [anthropics/skills](https://github.com/anthropics/skills) | Apache-2.0 | 96 |
| `autonomous-loops` | orchestration | core | [affaan-m/ECC](https://github.com/affaan-m/ECC) | MIT | 612 |
| `eval-harness` | orchestration | core | [affaan-m/ECC](https://github.com/affaan-m/ECC) | MIT | 306 |
| `loop-design-check` | orchestration | core | [affaan-m/ECC](https://github.com/affaan-m/ECC) | MIT | 144 |
| `mcp-builder` | orchestration | core | [anthropics/skills](https://github.com/anthropics/skills) | Apache-2.0 | 237 |
| `agent-architecture-audit` | orchestration | extra | [affaan-m/ECC](https://github.com/affaan-m/ECC) | MIT | 258 |
| `agent-harness-construction` | orchestration | extra | [affaan-m/ECC](https://github.com/affaan-m/ECC) | MIT | 75 |
| `agentic-os` | orchestration | extra | [affaan-m/ECC](https://github.com/affaan-m/ECC) | MIT | 389 |
| `autonomous-agent-harness` | orchestration | extra | [affaan-m/ECC](https://github.com/affaan-m/ECC) | MIT | 272 |
| `claude-code` | orchestration | extra | skills pessoais do autor | MIT | 746 |
| `claude-devfleet` | orchestration | extra | [affaan-m/ECC](https://github.com/affaan-m/ECC) | MIT | 113 |
| `codex` | orchestration | extra | skills pessoais do autor | MIT | 152 |
| `continuous-agent-loop` | orchestration | extra | [affaan-m/ECC](https://github.com/affaan-m/ECC) | MIT | 47 |
| `cost-aware-llm-pipeline` | orchestration | extra | [affaan-m/ECC](https://github.com/affaan-m/ECC) | MIT | 189 |
| `dynamic-workflow-mode` | orchestration | extra | [affaan-m/ECC](https://github.com/affaan-m/ECC) | MIT | 125 |
| `gan-style-harness` | orchestration | extra | [affaan-m/ECC](https://github.com/affaan-m/ECC) | MIT | 280 |
| `herdr-orchestrator` | orchestration | extra | skills pessoais do autor | MIT | 793 |
| `langchain-architecture` | orchestration | extra | [wshobson/agents](https://github.com/wshobson/agents) | MIT | 274 |
| `mcp-server-patterns` | orchestration | extra | [affaan-m/ECC](https://github.com/affaan-m/ECC) | MIT | 71 |
| `opencode` | orchestration | extra | skills pessoais do autor | MIT | 220 |
| `orch-pipeline` | orchestration | extra | [affaan-m/ECC](https://github.com/affaan-m/ECC) | MIT | 122 |
| `plan-orchestrate` | orchestration | extra | [affaan-m/ECC](https://github.com/affaan-m/ECC) | MIT | 264 |
| `ralphinho-rfc-pipeline` | orchestration | extra | [affaan-m/ECC](https://github.com/affaan-m/ECC) | MIT | 69 |
| `dispatching-parallel-agents` | teams | core | [obra/superpowers](https://github.com/obra/superpowers) | MIT | 168 |
| `multi-reviewer-patterns` | teams | core | [wshobson/agents](https://github.com/wshobson/agents) | MIT | 128 |
| `subagent-driven-development` | teams | core | [obra/superpowers](https://github.com/obra/superpowers) | MIT | 569 |
| `task-coordination-strategies` | teams | core | [wshobson/agents](https://github.com/wshobson/agents) | MIT | 164 |
| `using-git-worktrees` | teams | core | [obra/superpowers](https://github.com/obra/superpowers) | MIT | 168 |
| `bmad-party-mode` | teams | extra | [bmad-code-org/BMAD-METHOD](https://github.com/bmad-code-org/BMAD-METHOD) | MIT | 61 |
| `dmux-workflows` | teams | extra | [affaan-m/ECC](https://github.com/affaan-m/ECC) | MIT | 193 |
| `iterative-retrieval` | teams | extra | [affaan-m/ECC](https://github.com/affaan-m/ECC) | MIT | 213 |
| `on-call-handoff-patterns` | teams | extra | [wshobson/agents](https://github.com/wshobson/agents) | MIT | 71 |
| `parallel-execution-optimizer` | teams | extra | [affaan-m/ECC](https://github.com/affaan-m/ECC) | MIT | 75 |
| `parallel-feature-development` | teams | extra | [wshobson/agents](https://github.com/wshobson/agents) | MIT | 175 |
| `review-agent-setup` | teams | extra | [wshobson/agents](https://github.com/wshobson/agents) | MIT | 171 |
| `santa-method` | teams | extra | [affaan-m/ECC](https://github.com/affaan-m/ECC) | MIT | 308 |
| `team-agent-orchestration` | teams | extra | [affaan-m/ECC](https://github.com/affaan-m/ECC) | MIT | 112 |
| `team-builder` | teams | extra | [affaan-m/ECC](https://github.com/affaan-m/ECC) | MIT | 170 |
| `unified-memory` | teams | extra | [affaan-m/ECC](https://github.com/affaan-m/ECC) | MIT | 200 |
| `architecture-decision-records` | thinking | core | [wshobson/agents](https://github.com/wshobson/agents) | MIT | 442 |
| `blueprint` | thinking | core | [affaan-m/ECC](https://github.com/affaan-m/ECC) | MIT | 107 |
| `bmad-forge-idea` | thinking | core | [bmad-code-org/BMAD-METHOD](https://github.com/bmad-code-org/BMAD-METHOD) | MIT | 108 |
| `bmad-spec` | thinking | core | [bmad-code-org/BMAD-METHOD](https://github.com/bmad-code-org/BMAD-METHOD) | MIT | 161 |
| `brainstorming` | thinking | core | [obra/superpowers](https://github.com/obra/superpowers) | MIT | 251 |
| `discernment-nudge` | thinking | core | [anthropics/skills](https://github.com/anthropics/skills) | Apache-2.0 | 210 |
| `skill-creator` | thinking | core | [anthropics/skills](https://github.com/anthropics/skills) | Apache-2.0 | 486 |
| `spike` | thinking | core | skills pessoais do autor | MIT | 198 |
| `writing-plans` | thinking | core | [obra/superpowers](https://github.com/obra/superpowers) | MIT | 172 |
| `agent-self-evaluation` | thinking | extra | [affaan-m/ECC](https://github.com/affaan-m/ECC) | MIT | 183 |
| `before-you-build` | thinking | extra | [wshobson/agents](https://github.com/wshobson/agents) | MIT | 51 |
| `blocked-page-recovery` | thinking | extra | skills pessoais do autor | MIT | 138 |
| `bmad-advanced-elicitation` | thinking | extra | [bmad-code-org/BMAD-METHOD](https://github.com/bmad-code-org/BMAD-METHOD) | MIT | 65 |
| `bmad-brainstorming` | thinking | extra | [bmad-code-org/BMAD-METHOD](https://github.com/bmad-code-org/BMAD-METHOD) | MIT | 81 |
| `bmad-prfaq` | thinking | extra | [bmad-code-org/BMAD-METHOD](https://github.com/bmad-code-org/BMAD-METHOD) | MIT | 134 |
| `context-budget` | thinking | extra | [affaan-m/ECC](https://github.com/affaan-m/ECC) | MIT | 137 |
| `deep-research` | thinking | extra | [affaan-m/ECC](https://github.com/affaan-m/ECC) | MIT | 171 |
| `dev-team` | thinking | extra | [affaan-m/ECC](https://github.com/affaan-m/ECC) | MIT | 204 |
| `grounded-citations` | thinking | extra | skills pessoais do autor | MIT | 254 |
| `postmortem-writing` | thinking | extra | [wshobson/agents](https://github.com/wshobson/agents) | MIT | 234 |
| `prompt-engineering-patterns` | thinking | extra | [wshobson/agents](https://github.com/wshobson/agents) | MIT | 145 |
| `research-ops` | thinking | extra | [affaan-m/ECC](https://github.com/affaan-m/ECC) | MIT | 114 |
| `scan` | thinking | extra | [wshobson/agents](https://github.com/wshobson/agents) | MIT | 219 |
| `strategic-compact` | thinking | extra | [affaan-m/ECC](https://github.com/affaan-m/ECC) | MIT | 157 |
| `token-budget-advisor` | thinking | extra | [affaan-m/ECC](https://github.com/affaan-m/ECC) | MIT | 135 |
| `writing-skills` | thinking | extra | [obra/superpowers](https://github.com/obra/superpowers) | MIT | 680 |

## Terceiros citados no material de apoio

- **affaan-m/ECC** (MIT) — o schema de `hooks/configs/cursor.hooks.json` foi derivado do
  arquivo `.cursor/hooks.json` daquele repositório; o `hooks/README.md` marca isso como
  não conferido na documentação oficial do Cursor.
- **obra/superpowers** (MIT) — a ideia de `install` por harness e o vocabulário de
  fluxo (brainstorm → plano → subagentes → review) vêm do README dele.
- Os dossiês em `research/` foram produzidos por pesquisa própria (web + API do GitHub)
  e trazem, cada um, a contagem de itens marcados como **NAO_VALIDADO**.
- Fontes de documentação oficial usadas: `agentskills.io/specification`, docs de Claude
  Code, Codex, OpenCode, Prime Agent (local) e Hermes Agent (local).
