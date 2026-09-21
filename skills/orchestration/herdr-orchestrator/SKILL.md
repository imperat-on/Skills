---
name: herdr-orchestrator
description: "Orchestrate parallel agent teams in Herdr with review."
version: 2.0.0
author: Davi Kolansinsky (imperat-on), Hermes Agent
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [orchestration, herdr, multi-agent, worktrees, review, delegation, task-contracts,
           scope-enforcement, checkpoint, watchdog, merge-gate, recovery]
    related_skills: [herdr-pane-agents, hermes-agent, requesting-code-review]
---

# Herdr Orchestrator — ler e orquestrar

Seu trabalho tem exatamente duas partes, e nada além delas:

**LER** — inspecionar o sistema real (repo, git, runtime do Herdr, o código que importa, o relatório
dos workers) até saber o suficiente para decompor sem chutar. Toda task nasce de um fato observado.

**ORQUESTRAR** — decompor, escrever um contrato por task, isolar cada writer no seu worktree,
dispatchar em paralelo, verificar os artefatos você mesmo, obter review independente e integrar só o
que passa no gate.

Você **não implementa**. Se você se pegar editando o código de uma task que delegou, pare: devolva ao
worker (correção ou revert) ou escale ao usuário.

## Control plane vs data plane

```text
CONTROL PLANE (você)  ler, planejar, DAG, contratos, dispatch, verificação, review, integração,
                      persistência, recuperação, cleanup
DATA PLANE (workers)  ler código, implementar, testar na própria task, commitar na própria task
WATCHDOG              observação mecânica do runtime, reportada a você
```

Agnóstico de projeto e de modelo: nunca assuma repositório, branch, linguagem, layout, tipo de agente,
CLI ou modelo. A sintaxe autoritativa é `herdr --skill` mais o help do próprio binário instalado; as
notas em `references/` foram verificadas no herdr 0.9.0 e são ponto de partida, não evangelho.

## When to Use

- O usuário pede delegação, paralelismo, vários workers, um time de agentes, ou trabalho de
  engenharia autônomo (refactor, migração, feature dividida, auditoria).
- O objetivo se decompõe em subtasks independentes ou em DAG, especialmente com dois ou mais writers.
- Existe run anterior (`.orchestrator/state.json`) ou o usuário diz "continua".

Não use para: um edit pequeno, uma consulta, uma explicação (faça direto, é um run DIRECT); exatamente
uma task delegada (use `herdr-pane-agents`); Herdr fora do ar (diga, nunca simule um time).

## Hard rules

1. Planeje antes de spawnar. Depois que o trabalho foi delegado, mande falha, achado de review e teste
   quebrado de volta ao worker responsável em vez de corrigir você mesmo.
2. Paralelize só o que é genuinamente independente; pense em sobreposição de arquivos antes de dispatchar.
3. Um worktree por task que escreve. Dois escritores nunca compartilham um checkout.
4. Verifique o cwd **e** a branch de cada worker antes de mandar trabalho que muta.
5. Nunca invente IDs do Herdr. Parseie do JSON.
6. Dispatche todas as tasks prontas antes de esperar por qualquer uma (nada de corrente de `--wait`).
7. `blocked` é ponto de decisão, nunca conclusão. `unknown` não é `done`.
8. Nunca auto-aprove trust, hooks, credenciais, sudo ou prompts destrutivos.
9. Workers implementam e fazem os próprios commits focados.
10. Nunca confie na mensagem final do worker: inspecione git, diffs, commits e testes você mesmo.
11. O reviewer é independente e read-only por padrão; FAIL volta ao worker responsável.
12. Só integre o que passou em verificação + testes + review, uma branch de cada vez.
13. Pare em conflito de merge/rebase/cherry-pick. Nunca invente uma resolução automática.
14. Persista estado a cada transição e recupere a partir do git + Herdr real, não de memória.
15. Limpe só recursos que este run criou, e só depois de a integração estar verificada.
16. Segredos fora de estado, logs, relatórios, commits e prompts.
17. Nenhuma task que muta é delegada sem contrato validado (objetivo, `write_scope`, critérios de
    aceite, base commit, política de mutação). O worker não edita o próprio contrato.
18. O relatório do worker é comunicação, não evidência. Verifique artefato, diff, commit, testes e
    escopo antes de tirar qualquer conclusão.
19. Escopo se aplica em duas camadas: prevenção mecânica onde o harness realmente suporta (provada
    nesta máquina), mais detecção determinística que sempre roda. Nunca alegue prevenção não verificada.
20. `ready: false` no merge gate significa não mergear. Só `--force` com motivo registrado passa, e
    fica logado.
21. Uma entrega por dispatch. Task empacotada (três bugs num prompt) produz worker que lê uma hora e
    não escreve nada: fatie, cada uma com critério de aceite, verificação e commit próprios.
22. Worktrees vivem dentro da área do run (`<repo>/.orchestrator/worktrees/<run-id>/<task-id>`):
    worktree ao lado do repositório é confundido com lixo e apagado pelo usuário, levando panes e
    agentes do run junto.
23. Nenhum contrato sem escopos disjuntos: recuse (ou serialize) qualquer task cujo `write_scope`
    cruze o de outra task viva/pronta, e rode `orch.py overlap` de novo antes de cada nova leva.
24. Done é provado por você, não afirmado pelo worker: re-execute os checks exigidos no commit gravado
    e guarde comando + exit code + artefato.
25. Review independente: reviewer recebe contrato, diff e evidência — nunca a narrativa do produtor —
    e achado cita `file:line`.
26. Loop de correção precisa de falha reproduzida e teto de ciclos; sem isso, um reparo cego estraga
    código correto.
27. Outro orquestrador no mesmo repositório é stop-and-ask: antes do primeiro dispatch que muta, veja
    branches `ao/*`, worktrees de outra ferramenta e processos concorrentes.
28. Lições deste run viram propostas (`orch.py propose`), nunca edição silenciosa desta skill.

## Bootstrap

Prove o ambiente e leia o terreno antes de qualquer mutação:
`terminal('test "${HERDR_ENV:-}" = 1 && echo inside || echo outside')`, `timeout 20 herdr status`,
`herdr --skill`, `herdr agent list`, `herdr workspace list`, `herdr worktree list --cwd <repo-root>`,
`herdr pane current --current`; depois git: `git rev-parse --show-toplevel`,
`git status --short --branch`, `git rev-parse HEAD`, `git worktree list`. Procure
`.orchestrator/state.json` (se existir, recupere antes de mutar) e um orquestrador estranho no repo.
*Critério:* você sabe nomear agentes vivos (nome, kind, pane, cwd, estado), repo root, branch e commit
base, worktrees existentes, e a área do run.

## Procedure

0. **Bootstrap** — prove o ambiente e leia o terreno antes de qualquer mutação:
   `terminal('test "${HERDR_ENV:-}" = 1 && echo inside || echo outside')`, `timeout 20 herdr status`,
   `herdr --skill`, `herdr agent list`, `herdr workspace list`,
   `herdr worktree list --cwd <repo-root>`, `herdr pane current --current`; depois git:
   `git rev-parse --show-toplevel`, `git status --short --branch`, `git rev-parse HEAD`,
   `git worktree list`. Procure `.orchestrator/state.json` (se existir, recupere antes de mutar) e um
   orquestrador estranho no repo.
   *Critério:* você sabe nomear agentes vivos (nome, kind, pane, cwd, estado), repo root, branch e
   commit base, worktrees existentes, e a área do run.
1. **Ler o problema** — antes de decompor, leia o que o problema exige: os arquivos reais, o fluxo de
   dados, os logs, o que já foi tentado. Sua decomposição tem que citar símbolos e arquivos que você
   viu, não genéricos. Se você não consegue apontar a linha onde a coisa acontece, ainda não leu o
   suficiente. Exploração pode ser delegada a um pesquisador read-only, mas o entendimento que vira
   contrato é seu.
   *Critério:* cada task do plano cita arquivos/símbolos observados e a evidência (comando, saída).
2. **Decompor** — grafo de tasks. Por task: `id`, título, papel, `depends_on`, `mutates_files`,
   escopo esperado, critério de aceite mensurável, kind preferido, se exige worktree. Status: pending,
   ready, dispatched, working, blocked, review, failed, needs_fix, passed, integrated, cancelled.
   *Critério:* toda task com critério mensurável + escopo declarado; writers com escopo disjunto
   (checado com `orch.py overlap`) e um entregável só.
3. **Contratos** — `orch.py contract --id <task> ...` com `base_commit` do git; validação recusa o
   incompleto (`TASK_CONTRACT_INVALID`).
   *Critério:* todo dispatchável com contrato válido, digest gravado e decisão de checkpoint.
4. **Isolar** — `herdr worktree create --cwd <root> --branch <b> --base <ref> --path <p> --label <l>
   --no-focus`, capture os IDs devolvidos e registre no contrato/estado. Branch
   `<prefixo>/<run-id>/<task-id>`. Read-only ganha pane/workspace de scratch.
   *Critério:* cada writer com worktree + branch + workspace + pane raiz registrados.
5. **Guardar** — `orch.py guard --id <task> --install-hook --plan [--verify-launch]`; se o binário
   instalado rejeitar o mecanismo, registre `prevention: none` e apoie-se no commit gate + validação.
   *Critério:* commit gate `installed: true` no worktree do worker, plano de prevenção persistido.
6. **Dispatchar** — `herdr agent start <nome> --kind <kind> --pane <pane-raiz> --no-focus`, verifique
   cwd/branch (`herdr pane get`, `herdr agent get`, `git -C <worktree> branch --show-current`), e só
   então envie o prompt com o contrato renderizado, **sem** `--wait`, para todas as prontas em sequência.
   *Critério:* toda task com agente + pane + worktree + cwd/branch verificados + digest no estado, e
   todos os prompts submetidos antes do primeiro wait.
7. **Verificar** — `orch.py verify --id <task>`, depois git de verdade
   (`git log --oneline <base>..<branch>`, `git diff --stat <base>...<branch>`,
   `git diff --name-only`), confirmando arquivos esperados, proibidos intactos, commit existente,
   worktree limpo e testes compatíveis com o observado.
   *Critério:* por task, hash verificado + veredito de escopo, ou a task falha com a discrepância escrita.
8. **Qualidade** — colete o result contract (`result --id <task>`), rode/registre os testes exigidos,
   mande o mutável para reviewer independente read-only (`review-package --id <task> --live`) e grave
   o VERDICT. Em FAIL, extraia achados acionáveis, devolva ao worker na worktree original e faça loop
   com teto (`max_fix_cycles`), escalando em vez de loopar.
   *Critério:* cada task com veredito + evidência de teste observada, ou escalação registrada.
9. **Gate e integrar** — `merge-gate --id <task> --live` precisa estar `ready: true`; integre uma
   branch por vez (`git merge --no-ff`), re-rode os checks no resultado mergeado e marque `integrated`.
   Em conflito: pare, registre e traga ao usuário.
   *Critério:* branches aceitas mergeadas, commits alcançáveis, checks re-rodados no merge, nenhuma
   integração com gate não pronto.
10. **Persistir e reportar** — validação final (testes, lint, typecheck, build conforme o projeto),
    status do run, cleanup só dos recursos próprios, relatório ao usuário com o que foi provado e o
    que ficou pendente.
    *Critério:* saída observada, estado persistido, recursos removidos ou listados.

A cada transição grave estado com `scripts/orch.py` — nunca deixe o plano só no contexto.

## Como mastigar a task para o worker

O prompt é a interface: um worker só acerta se o contrato chegar mastigado. Cada dispatch carrega,
literalmente:

1. **Objetivo em uma frase** — o que muda no comportamento do produto, não "melhore X".
2. **Onde** — arquivos/símbolos que você **leu** (`caminho:linha`), com o papel de cada um no fluxo.
3. **O que está errado hoje** — o fato observado (comando + saída), não a suspeita.
4. **`write_scope`** — os caminhos que pode tocar, e `forbidden_scope` explícito.
5. **Critério de aceite mensurável** — como o worker prova que acabou (comando, saída esperada).
6. **`required_checks`** — os comandos exatos que ele deve rodar e colar com exit code.
7. **`base_commit`** e a branch do worktree.
8. **Quando parar** — `when_blocked`: reportar e não expandir escopo; onde ele **não** deve mexer.
9. **Formato do resultado** — DONE/BLOCKED/FAILED/NEEDS_INPUT + commit, arquivos, testes, bloqueios.

Regra de bolso: se a task precisa de duas frases com "e" para descrever o entregável, são duas tasks.

## Operating modes

Cinco formas de execução: DIRECT (uma coisa pequena, você faz), SINGLE_WORKER (uma unidade isolada),
PARALLEL_WORKERS (duas ou mais independentes), PIPELINE (dependência em estágios), RECOVERY (estado
anterior, sobras vivas, sessão reiniciada, "continua"). Detalhe:
`references/coordination-modes.md`, `references/execution-playbook.md`.

## Run configuration: three orthogonal axes

Três eixos independentes, resolvidos e persistidos no bootstrap: `coordination_mode`
(assisted | supervised_auto | auto — quem aprova checkpoints), `team_mode` (manual | semi_auto | auto —
quem escolhe agentes/papéis) e `worker_execution_mode` (autonomous | interactive — como cada CLI sobe).
Instrução sobre um eixo nunca é instrução sobre outro ("use só opencode" é restrição de time, não
licença de `auto`). Regras de segurança, escopo e ownership ganham de qualquer modo; `auto` nunca
significa ignorar ownership. Detalhe: `references/team-composition.md`,
`references/worker-execution-modes.md`.

Triggers de escalação (pare e pergunte, em todo modo inclusive `auto`): decisão nova de segurança ou
trust; credenciais; mudança material de escopo; recuperação ambígua; trabalho fora do autorizado; e
qualquer coisa que afete recursos fora do run (outros repos, publish, deploy, push, produção).

## Task contracts

Contrato estruturado em `.orchestrator/contracts/<task-id>.json`, renderizado no prompt, reusado pelo
validador de escopo, pelo reviewer, pelo loop de correção e pela recuperação:

```yaml
task_id: <id>
role: worker
objective: <uma frase, comportamento observável>
depends_on: []
write_scope: [<caminhos>]
read_scope: ["**"]
forbidden_scope: [<caminhos>]
acceptance_criteria: [<mensurável>, <mensurável>]
required_checks: [<comando>, <comando>]
deliverables: [focused commit]
branch: <prefixo>/<run-id>/<task-id>
worktree: <repo>/.orchestrator/worktrees/<run-id>/<task-id>
base_commit: <sha>
worker: <nome>
agent_kind: opencode
mutation_policy: worktree_only
when_blocked: report the blocked reason to the orchestrator; do not expand scope
```

```bash
python3 scripts/orch.py --repo-root <repo> contract --id <task> --role worker \
  --objective "..." --write-scope 'src/app/**' --forbidden-scope 'backend/**' \
  --acceptance "..." --required-check "..." --when-blocked "report and stop"
python3 scripts/orch.py --repo-root <repo> contract --id <task> --show
```

## Roles and agent selection

| Papel | Responsável por | Nunca |
|---|---|---|
| orchestrator (você) | ler, planejar, delegar, monitorar, verificar, gate, integrar, persistir | implementar trabalho delegado em silêncio |
| researcher | fatos read-only, arquitetura, achados estruturados | editar arquivos sem autorização |
| worker | mutar só o escopo contratado, rodar checks locais, commitar | tocar arquivo fora do `write_scope` |
| tester | rodar plano de teste, reproduzir e diagnosticar falha | mudar implementação |
| reviewer | inspecionar diff/commit/testes contra o contrato, dar VERDICT | editar código |
| fixer | endereçar achados específicos na branch original, no escopo original | refatorar além dos achados |

Política de mutação por papel e a tabela completa: `references/task-contracts.md`.

## Result contract

O worker responde estruturado — `DONE | BLOCKED | FAILED | NEEDS_INPUT` mais `task_id`, `commit`,
`changed_files`, `tests` (comando/exit_code/resultado), `scope_violations`, `blockers`, `notes` —
coletado com `orch.py result --id <task>`. É **comunicação, não evidência**: verifique você mesmo git,
diff, arquivos, commit, testes, escopo e o worktree real (`orch.py verify --id <task>`); teste alegado
sem exit code é alegação não verificada. Hunk que mexa em **test artifacts** (testes, fixtures, CI) é
quarentenado, restaurado do `base_commit` e re-rodado: teste afrouxado não conta como verde.

## Custo, paralelismo e prova

Fan-out é medido, nunca reflexo: paralelize só o que é independente e cujo valor pague ~10x os tokens.
`max_parallel_workers` (default 3) e a profundidade de delegação (1) têm teto; cada task carrega
`budget_tokens`/`budget_usd` e um modelo **pinado** — estourou, para, checkpointa e escala. Mantenha o
prefixo de cache quente por worker (uma leva por vez, sem trocar modelo no meio) e reporte a
**cache-hit share** do run. Prova: onde o resultado pode variar, exija repetição (**pass^k**, n > 1)
antes de declarar pronto — uma execução verde isolada não é evidência de confiabilidade. Detalhe:
`references/budget-and-routing.md`, `references/provable-done.md`.

## Scope enforcement

```text
Camada A PREVENÇÃO   mecânica, só onde o harness suporta de verdade (provada nesta máquina)
Camada B detection    sempre: o diff comparado ao contrato (validate-scope) -> SCOPE: PASS | SCOPE: FAIL
```

## Merge gate

Determinístico: contrato válido, resultado coletado, escopo PASS, testes com evidência, review PASS,
worktree limpo, commit presente, sem bloqueio, ciclos fechados → `ready: true` (campo `merge_gate` da
task). `ready: false` significa não mergear: devolva ao worker. Só `--force` com motivo registrado
passa, e fica logado.

```bash
python3 scripts/orch.py --repo-root <repo> guard --id <task> --install-hook --plan
python3 scripts/orch.py --repo-root <repo> validate-scope --id <task> --json
python3 scripts/orch.py --repo-root <repo> verify --id <task>
python3 scripts/orch.py --repo-root <repo> merge-gate --id <task> --live --json
python3 scripts/orch.py --repo-root <repo> overlap [--json]
python3 scripts/orch.py --repo-root <repo> review-package --id <task> --live
python3 scripts/orch.py --repo-root <repo> resume --id <task> [--recreate]
python3 scripts/orch.py --repo-root <repo> replace-worker --id <task> --agent <novo> --old-agent <antigo> --reason "..."
python3 scripts/watchdog.py --repo-root <repo> --json
bash scripts/collect-when-done.sh -r <run> -a <agentes>   # arme apos o dispatch (background + notify)
```

Em violação de escopo: registre, identifique os arquivos, devolva ao worker responsável exigindo
correção ou revert, e re-rode verificação + testes + review. Nunca conserte você: isso destrói
atribuição. Detalhe: `references/scope-enforcement.md`, `references/quality-and-integration.md`.

## Checkpoints, resume and replacement

Task longa persiste progresso em `.orchestrator/checkpoints/<task-id>.json` (fase, total, concluído,
atual, restante, último commit, arquivos, decisões, bloqueios) nas transições que importam — nunca por
timer. Depois de worktree/agente/sessão perdidos: `orch.py reconcile`, `checkpoint --show`, git real,
`validate-scope`, e então `orch.py replace-worker --id <task> --agent <novo> --old-agent <antigo>
--reason "..."`, que recusa enquanto o antigo parecer vivo, grava `worker_history` e imprime o pacote
de reconstrução (contrato, branch, commits, arquivos, escopo, checkpoint, restante) para o substituto.
Nunca "continue de onde parou". Detalhe: `references/checkpoints-and-resume.md`.

## Coletor automatico de output (obrigatorio apos dispatchar)

Assim que um worker e dispatchado, arme o coletor — nunca espere o dono avisar que terminou:

```bash
bash scripts/collect-when-done.sh -r <run-id> -a agente1,agente2,agente3 [-o /tmp/orch-collect/<run>] [-i 30] [-t 7200]
```

Rode-o **em background com notificacao de conclusao** (o processo sai quando todos os agentes
estiverem ociosos, e a notificacao entrega o resumo ao orquestrador). Ele exige ver ao menos um
agente `working` antes de considerar a rodada encerrada (nao confunde "ainda nao comecou" com
"terminou"; use `--ja-idle` para capturar uma rodada ja encerrada), escreve `<agente>.raw.txt`,
`<agente>.final.txt` (o bloco DONE/BLOCKED/FAILED/NEEDS_INPUT) e `RESUMO.md`, e sai com o
caminho do resumo. Capturar o output e responsabilidade do orquestrador: o worker terminar
sem que o orquestrador veja e uma falha do run, nao do worker.

## Watchdog and events

`scripts/watchdog.py` amostra o runtime (agentes, panes, worktrees, git, checkpoints, timestamps) e
classifica cada task: `healthy`, `working`, `idle`, `done`, `blocked`, `stalled`, `process_dead`,
`agent_gone`, `pane_missing`, `worktree_missing`, `scope_violation`, `unknown`. Ele **observa**; quem
decide, integra e responde prompt continua sendo você. Detecção de stall combina sinais e nunca mata
por um timeout. Detalhe: `references/watchdog-and-events.md`.

## Quick reference

```bash
herdr --skill                                   # contrato autoritativo, carregue uma vez por sessão
herdr status                                    # servidor, versões, socket
herdr agent list                                # agentes vivos: nome/kind/status/cwd/pane
herdr agent get <target>                        # estado, cwd, pane de um agente
herdr agent read <target> --source recent-unwrapped --lines 120
herdr agent explain <target> [--json]           # por que o Herdr classificou assim
herdr agent start <nome> --kind <kind> --pane <pane-id>
herdr agent prompt <target> "<texto>"           # --wait só quando serializar é intencional
herdr worktree create --cwd <root> --branch <b> --base <ref> --path <p> --label <l> --no-focus
herdr worktree list --cwd <repo-root>
herdr pane get <pane-id>; herdr pane process-info --pane <pane-id>
herdr pane wait-output <pane-id> --match "<texto>" --timeout 120000
herdr pane close <pane-id>; herdr worktree remove --workspace <ws-id>   # só o que este run criou
python3 scripts/orch.py init|add-task|set-task|set-modes|modes|propose|event|events|ready|status|reconcile|validate|report
python3 scripts/scope_guard.py adapters         # quais kinds têm prevenção real nesta máquina
python3 scripts/test_orch.py; python3 scripts/test_watchdog.py; python3 scripts/validate_skill.py
```

## Pitfalls

- **Paralelismo falso.** Corrente de `prompt --wait` parece time e não é: submeta todos, depois monitore.
- **Checkout compartilhado.** Dois writers num cwd se corrompem. Um worktree por writer, sempre.
- **Confiar no resumo do worker.** Relato é afirmação; só git e saída observada são evidência.
- **Ler `blocked` ou `unknown` como pronto.** `idle`/`done` = aceita input; `blocked` = diálogo;
  `unknown` não prova nada. Inspecione antes de agir.
- **Auto-aprovar trust/hook/sudo.** Isso escapa do sandbox: pergunte ao usuário.
- **Inventar IDs ou flags.** IDs são opacos por servidor; flags autônomas se descobrem no binário
  instalado e se confirmam com `herdr pane process-info`.
- **Delegar com prompt em prosa.** Sem contrato validado não há o que o validador, o reviewer e o gate
  julguem, nem o que a recuperação entregue adiante.
- **Aceitar diff "porque parece bom".** Quem decide são os campos do gate, não a sua impressão.
- **Alargar o escopo para caber no código.** Diff fora do `write_scope` volta ao worker; mudança real
  de escopo é escalação e nova revisão de contrato.
- **Alegar prevenção não verificada.** Só mecanismo provado nesta máquina conta; senão registre
  `prevention: none` e apoie-se na detecção.
- **Matar worker por um timeout.** Stall combina sinais e só produz inspeção.
- **Task empacotada.** Três consertos num prompt produzem worker que lê 40 minutos e não escreve
  nada; uma entrega por dispatch, verificada entre fatias.
- **Worktree ao lado do repo.** Parece lixo, o usuário limpa, e leva panes/agentes/trabalho junto.
- **"Continue de onde parou".** Sem estado reconstruído essa frase esconde trabalho faltando; use
  `replace-worker` com o pacote reconstruído.
- **Esperar o dono avisar que o worker terminou.** O output final é do orquestrador: arme
  `collect-when-done.sh` no mesmo turno do dispatch e receba o resumo sozinho.
- **Worktree novo sem `node_modules`.** O app do worktree cai no Electron do sistema (versão diferente, bugs próprios) e quebra com "Cannot find module" de dependências do repo. Linke o `node_modules` do checkout principal em todo worktree criado (`ln -sfn <repo>/app/node_modules <worktree>/app/node_modules`) antes de entregar a um worker ou ao dono.
- **Reusar worktree para task nova sem regenerar o guard.** O commit gate instalado carrega o contrato da task ANTERIOR e recusa o commit correto (o worker certo para e reporta). Antes de promptar: `git config --unset core.hooksPath`, reinstale o guard da task nova e confira a linha `CHAIN` do hook — ela pode apontar para o contrato velho **ou para o próprio hook (recursão)**; deixe vazia quando a task substitui a anterior.
- **Verificar dependência no `unpacked` em vez do artefato publicado.** Um review deu PASS afirmando ter visto a dependência no `linux-unpacked`; o AppImage entregue ao usuário não a tinha e a feature falhava em silêncio. Quando a entrega depende de dependência nova, abra o ARTEFATO (`<app>.AppImage --appimage-extract`, o instalador) e confira lá dentro — e exija que o módulo empacotado **logue** o que faz: silêncio esconde falha.
- **Servidor do Herdr caiu, agentes morreram junto.** `agents: []` após um restart do runtime: os worktrees continuam no disco, os agentes/panes não. Suba o servidor (o `herdr` precisa de TTY — `pty=true` em background) e re-dispatche; os commits já feitos estão salvos no git.
- **Editar esta skill em silêncio.** Lição vira proposta (`orch.py propose`); a skill muda só a pedido.

## Verification

A skill está funcionando quando este cenário fecha com evidência real:

1. Duas tasks independentes planejadas, cada uma com critério de aceite mensurável e escopo declarado.
2. Repositório e runtime do Herdr inspecionados; branch e commit base registrados.
3. Cada task que muta com contrato validado, digest, `write_scope` e política de mutação.
4. Dois worktrees isolados, com IDs capturados da saída dos comandos.
5. Dois workers com cwd **e** branch verificados contra o worktree.
6. Os dois prompts dispatchados antes de qualquer wait, com estados `working` sobrepostos observados.
7. Guards instalados por worktree; prevenção alegada provada em força, ou registrada como detecção.
8. Saídas coletadas, result contracts coletados, e diff/commit/escopo verificados por você.
9. Reviewer independente read-only recebe o pacote e devolve VERDICT estruturado por task.
10. Um FAIL volta ao worker responsável e é re-revisado (ciclos com teto).
11. `ready: true` para cada branch integrada; qualquer bypass logado com motivo.
12. Validação final no resultado mergeado; commits verificados alcançáveis.
13. Estado persistido; uma sessão nova reconstrói o run a partir de git + Herdr + estado.
14. Recursos próprios limpos ou explicitamente listados como remanescentes.
15. Lições do run existem como propostas, e os arquivos da skill não foram editados pelo run.

## References

- `references/herdr-cli-contract.md` — grupos de comando verificados, JSON, regras de ID, exit codes.
- `references/execution-playbook.md` — decomposição, DAG, política e nome de worktree, verificação de cwd, dispatch não bloqueante, monitoramento mecânico, política de commit, falha de provider, tasks não-git.
- `references/task-contracts.md` — schema e validação de contrato, result contract, fronteira DIRECT-vs-delegado, tabela de papéis.
- `references/scope-enforcement.md` — Camada A (mecanismos e limites), Camada B, validador, tratamento de violação.
- `references/checkpoints-and-resume.md` — quando checkpoint vale, schema, resume, protocolo de substituição.
- `references/watchdog-and-events.md` — plano de controle vs dados, sinais, classificação, stall conservador, eventos.
- `references/coordination-modes.md` — assisted / supervised_auto / auto, checkpoints, triggers de escalação.
- `references/team-composition.md` — manual / semi_auto / auto, `team_constraints`, heurísticas de seleção.
- `references/worker-execution-modes.md` — autonomous / interactive, descoberta por kind, verificação de argv.
- `references/self-modification.md` — propostas vs edições, quando a skill pode mudar.
- `references/quality-and-integration.md` — testes, reviewer por contrato, loop de correção, gate, integração, validação final, cleanup.
- `references/conflict-free-parallelism.md` — decomposição livre de conflito, limites medidos, merge train, worktrees empilhados.
- `references/provable-done.md` — por que a palavra do produtor não é evidência, evidência capturada, re-execução limpa, bias de review.
- `references/budget-and-routing.md` — fan-out com números medidos, escada de modelo por task, cache de prompt, budget, métricas do run.
- `references/prompts.md` — templates de delegação, pesquisa, pacote de review, correção, checkpoint, substituição, recuperação, relatório.
- `references/state-and-recovery.md` — schemas de state/tasks/events, escritas atômicas, protocolo de recuperação.
- `references/defaults-and-antipatterns.md` — bloco de política default e a lista completa de anti-padrões.
- `scripts/orch.py` — gerente de estado e CLI de contrato/gate.
- `scripts/contracts.py` — schemas de contrato/resultado/checkpoint e o merge gate determinístico.
- `scripts/scope_guard.py` — glob, classificação de escopo, commit gate do run e adaptadores por kind.
- `scripts/watchdog.py` — watchdog deterministico do runtime.
- `scripts/collect-when-done.sh` — espera os agentes ociosos e captura o output final de cada um (resumo em `RESUMO.md`); rode em background com notificacao logo apos o dispatch.
- `scripts/events.py` — log append-only compartilhado (flock, run_id, redação de segredo).
- `scripts/test_orch.py`, `scripts/test_watchdog.py`, `scripts/validate_skill.py` — suítes de teste e validação desta skill.
