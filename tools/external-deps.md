## Skills que dependem de ferramenta externa

Estas não são autossuficientes: sem o binário/serviço, a instrução continua
legível, mas o agente não consegue executar o fluxo.

| Skill | Precisa de |
|---|---|
| `caveman-compress` | `ANTHROPIC_API_KEY` (o script da skill chama a API direto) |
| `worktrunk` | CLI `wt` (worktrunk) instalado |
| `browser-qa`, `e2e-testing`, `dogfood`, `webapp-testing` | navegador / Playwright |
| `mcp-builder`, `mcp-server-patterns` | SDK do MCP (`@modelcontextprotocol/sdk` ou Python) |
| `claude-code`, `codex`, `opencode` | a CLI correspondente instalada |
| `herdr-orchestrator` | Herdr (e os workers em panes) |
| `vercel-react-best-practices`, `vercel-react-view-transitions` | projeto React 18+/Next |
| `deep-research` | MCPs `firecrawl` e `exa` |

As skills do caveman **exceto** `caveman-compress` funcionam sem nada instalado —
são disciplina de prompt (saída curta, edição em pedaço, exploração read-only). As
que dependem do gateway Caveman Cloud (`caveman-learn`, `caveman-optimize`,
`caveman-setup`, `caveman-manage`, `caveman-discover`, `caveman-evidence-review`)
ficaram **fora** do kit de propósito.

O resto do catálogo não precisa de nada além de shell e leitura de arquivo.
