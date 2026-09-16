# 04 — Hooks (ganchos) para agentes CLI de código

> Pesquisa: 16/09/2026. Fontes primárias = docs oficiais (code.claude.com/docs/en/hooks),
> repositórios reais clonados em `/tmp` e validações via `gh api`. Scripts prontos,
> testados, em `research/hooks-raw/` (37/37 testes de fumaça passando).

## 0. Sumário executivo

Hooks são o ponto de **controle determinístico** sobre um agente que, de resto, é
probabilístico. O padrão que a comunidade convergiu (e que os repos com mais estrelas
implementam igual) é uma **pipeline de três camadas**:

| Camada | Evento | Papel | Exemplo |
|---|---|---|---|
| Prevenção | `PreToolUse` | negar antes de acontecer | bloquear `rm -rf`, `.env`, `git push main` |
| Correção | `PostToolUse` | formatar/lintar/typecheck/testar depois | prettier/ruff, `tsc --noEmit`, pytest |
| Feedback | `Stop` / `Notification` | gate de conclusão e aviso humano | suíte falhou → continua; ntfy/telegram |

Regra que separa hook amador de hook que funciona: **fail-open** (script quebrado não
trava a sessão) + **exit 2 só onde existe intenção de bloquear** + **nada de segredo
hardcoded** (env vars).

---

## 1. Schema oficial (docs.claude.com / code.claude.com/docs/en/hooks)

### 1.1 Onde se define (escopo)

| Local | Escopo | Versionável |
|---|---|---|
| `~/.claude/settings.json` | todos os seus projetos | não (local da máquina) |
| `.claude/settings.json` | um projeto | **sim, commitável** |
| `.claude/settings.local.json` | um projeto | não (gitignored) |
| Managed policy settings | organização inteira | sim (admin) |
| Plugin `hooks/hooks.json` | enquanto o plugin está ativo | sim (vai no plugin) |
| Frontmatter de skill | resto da sessão após invocar a skill | sim |
| Frontmatter de subagente | enquanto o subagente roda | sim |

- Entradas **se mesclam** entre níveis (user + projeto + local somam; não substituem).
- `allowManagedHooksOnly: true` bloqueia hooks de usuário/projeto/local (só managed passa).
- `disableAllHooks` só funciona fora do managed settings.
- `allowedHttpHookUrls` / `httpHookAllowedEnvVars` restringem hooks HTTP (URLs e env vars).
- Cloud sessions **não** leem `~/.claude/settings.json` — vêm do repo + settings do servidor.
- Hooks de settings/plugins **também rodam dentro de subagentes** (o input ganha `agent_id`/`agent_type`).

### 1.2 Estrutura de configuração (3 níveis de aninhamento)

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "if": "Bash(rm *)",
            "command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/block-rm.sh",
            "timeout": 5,
            "statusMessage": "checando comando..."
          }
        ]
      }
    ]
  }
}
```
(1) evento `PreToolUse` → (2) grupo de matcher `"Bash"` → (3) handler `type: command`.
O `if` corta ainda mais: só spawna o script para subcomandos que casam `rm *`.

Se o diretório atual sumir no meio da sessão, o hook roda a partir do diretório de
início da sessão → raiz do projeto → home → /tmp (na primeira que existir).

### 1.3 Matchers

| Valor do matcher | Como é avaliado | Exemplo |
|---|---|---|
| `"*"`, `""` ou ausente | casa com tudo | dispara em toda ocorrência |
| só letras/dígitos/`_`/`-`/espaço/`,`/`\|` | string exata, ou lista separada por `\|` ou `,` | `Bash`; `Edit\|Write`; `Edit, Write` |
| qualquer outro caractere | **regex JavaScript não ancorada** (`RegExp.test`) | `^Notebook`; `mcp__memory__.*` |

> `Edit.*` casa `Edit` **e** `NotebookEdit` (não ancorado). Use `^Edit$` para string inteira.
> `mcp__memory` (sem `.*`) é comparação exata e **não casa nada** — use `mcp__memory__.*`.

O que cada evento filtra:

| Evento | Matcher casa contra | Valores |
|---|---|---|
| PreToolUse, PostToolUse, PostToolUseFailure, PermissionRequest, PermissionDenied | nome da ferramenta | `Bash`, `Edit\|Write`, `mcp__.*` |
| SessionStart | como a sessão iniciou | `startup`, `resume`, `clear`, `compact`, `fork` |
| SessionEnd | por que terminou | `clear`, `resume`, `logout`, `prompt_input_exit`, `other` |
| Notification | tipo de notificação | `permission_prompt`, `idle_prompt`, `auth_success`, `elicitation_dialog`, ... |
| SubagentStart / SubagentStop | tipo do agente | `Explore`, `Plan`, nome custom |
| PreCompact / PostCompact | gatilho | `manual`, `auto` |
| FileChanged | nomes de arquivo | `.envrc\|.env` |
| `Stop`, `UserPromptSubmit`, `PostToolBatch`, `MessageDisplay`, `WorktreeCreate`, `WorktreeRemove`, `TaskCreated`, `TaskCompleted`, `TeammateIdle` | **sem suporte a matcher** | adicionar `matcher` é ignorado silenciosamente |

### 1.4 Tipos de handler (5)

| `type` | O que é | Observação |
|---|---|---|
| `command` | comando shell; JSON do evento no stdin | padrão de fato |
| `http` | POST do JSON do evento para uma URL | resposta usa o mesmo schema de saída |
| `mcp_tool` | chama tool de MCP server conectado; texto = stdout | SessionStart/Setup só suportam `command` e `mcp_tool` |
| `prompt` | manda o input + prompt para um modelo (Haiku default) → `{ok, reason, impossible}` | 30s timeout |
| `agent` | gera subagente com Read/Grep/Glob para verificar (experimental) | 60s timeout |

Campos comuns a todos: `type` (obrigatório), `if`, `timeout`, `statusMessage`, `once`
(`once` só vale em frontmatter de skill).
Campos de `command`: `command`, `args` (exec form: spawna direto, sem shell), `async`,
`asyncRewake` (roda em background e acorda o Claude no exit 2), `shell` (`bash`/`powershell`).

Timeouts default: **600s** em command/http/mcp_tool; **30s** em prompt; **60s** em agent.
Caem para 30s em UserPromptSubmit/PreModelSwitch/PostModelSwitch e 10s em MessageDisplay.
**SessionEnd tem budget de 1.5s** (sobe até 60s se você definir `timeout`, ou via
`CLAUDE_CODE_SESSIONEND_HOOKS_TIMEOUT_MS`).
Hook que estoura o timeout é **cancelado e seu output descartado** — em PreToolUse isso
significa **não bloquear** (não confie em hook lento como sua cerca).

### 1.5 Input comum (stdin de todo evento)

| Campo | Notas |
|---|---|
| `session_id` | id da sessão |
| `prompt_id` | UUID do prompt atual (correlaciona com OTel) |
| `transcript_path` | JSONL da conversa (escrito async — pode estar atrasado; use `last_assistant_message` no Stop) |
| `cwd` | diretório atual |
| `scratchpad_dir` | pasta de temporários da sessão |
| `permission_mode` | `default`, `plan`, `acceptEdits`, `auto`, `dontAsk`, `bypassPermissions` |
| `effort` | `{level: low|medium|high|xhigh|max}` + `$CLAUDE_EFFORT` no Bash |
| `hook_event_name` | nome do evento |
| `agent_id`, `agent_type` | só quando o hook roda dentro de subagente / `--agent` |

### 1.6 Exit codes

| Código | Efeito |
|---|---|
| **0** | sucesso. stdout vira JSON se começar com `{` e terminar com `}`. Em `UserPromptSubmit`, `UserPromptExpansion`, `SessionStart` e `PostModelSwitch`, stdout tratado como texto **entra no contexto do Claude** |
| **2** | **erro bloqueante**. Bloqueia em quem pode bloquear; a mensagem exibida é o `reason` do JSON ou, sem JSON, o **stderr** |
| **1 / outros** | sem JSON válido = **não bloqueia** (vira aviso "non-blocking status code"). `exit 1` NÃO é um bloqueio |

| Evento | Bloqueia no exit 2? | O que acontece |
|---|---|---|
| PreToolUse | **sim** | bloqueia a chamada da ferramenta |
| UserPromptSubmit | **sim** | rejeita e apaga o prompt |
| Stop / SubagentStop | **sim** | impede o término; conversa continua |
| PreCompact | **sim** | bloqueia a compactação |
| PostToolBatch | **sim** | para o loop antes da próxima chamada ao modelo |
| TaskCreated / TaskCompleted / TeammateIdle | sim | rollback da task / impede conclusão / mantém teammate ativo |
| PostToolUse / PostToolUseFailure | não | mostra o stderr ao Claude (a ferramenta **já rodou**) |
| Notification, SessionEnd, SessionStart, SubagentStart, Setup, PostCompact, PermissionDenied, StopFailure, InstructionsLoaded, MessageDisplay | não | saída ignorada (só efeito colateral) |

Formas de saída: **escolha uma** — ou exit code puro, ou `exit 0` + JSON. Misturar mantém
o bloqueio do exit 2 e ainda lê os campos JSON. Stdout com JSON inválido em evento de
decisão = erro não-bloqueante (a ação prossegue); exit 2 continua bloqueando.

### 1.7 JSON de saída

Campos universais:

| Campo | Default | Efeito |
|---|---|---|
| `continue` | `true` | `false` → Claude para de processar após o hook (tem precedência sobre tudo) |
| `stopReason` | — | mensagem mostrada ao usuário quando `continue: false` |
| `suppressOutput` | `false` | aceito e **ignorado** (não faz nada) |
| `systemMessage` | — | aviso exibido ao usuário |
| `terminalSequence` | — | sequência de escape que o Claude Code emite por você (OSC 0/1/2/9/99/777 e BEL). **É o jeito oficial de notificar o terminal** — hook não tem `/dev/tty` |
| `hookSpecificOutput` | — | objeto aninhado, exige `hookEventName` |

`additionalContext` (dentro de `hookSpecificOutput`) injeta texto no contexto do Claude,
embrulhado em system reminder, no ponto do evento. Escreva como **fato**, não como ordem
("The deployment target is production" em vez de "IGNORE…") — frases imperativas disparam
as defesas de prompt-injection e o texto é mostrado ao usuário em vez de virar contexto.
Limite: 10.000 caracteres por saída.

### 1.8 Matriz de decisão por evento

| Eventos | Padrão | Campos-chave |
|---|---|---|
| UserPromptSubmit, UserPromptExpansion, PostToolUse, PostToolUseFailure, PostToolBatch, Stop, SubagentStop, ConfigChange, PreCompact | `decision` no topo | `decision: "block"`, `reason` |
| PreToolUse | `hookSpecificOutput` | `permissionDecision` (`allow\|deny\|ask\|defer`), `permissionDecisionReason`, `updatedInput`, `additionalContext` |
| PermissionRequest | `hookSpecificOutput` | `decision.behavior` (`allow\|deny`), `updatedInput` |
| PermissionDenied | `hookSpecificOutput` | `retry: true` (diz ao modelo que pode tentar de novo) |
| SessionStart, SubagentStart, PostModelSwitch | só contexto | `additionalContext` (+ `initialUserMessage`, `sessionTitle`, `watchPaths`, `reloadSkills` no SessionStart) |
| Notification, SessionEnd, PostCompact, Setup, InstructionsLoaded, StopFailure, CwdChanged, DirectoryAdded, FileChanged | nenhum | só efeito colateral |
| WorktreeCreate | caminho no stdout | JSON inválido falha a criação |

Precedência entre hooks que decidem o mesmo PreToolUse: **deny > defer > ask > allow**.
`decision`/`reason` no topo em PreToolUse estão **depreciados** (`approve`/`block` →
`allow`/`deny`). PostToolUse tem ainda `updatedToolOutput` (substitui o resultado antes de
chegar ao Claude — precisa casar com o shape da ferramenta) e `classifierContext`.
Stop/SubagentStop têm `stop_hook_active` no input (para não entrar em loop) e o Claude Code
**desiste sozinho após 8 bloqueios consecutivos**.

---

## 2. Exemplo mínimo funcional de CADA evento relevante

Todos abaixo foram implementados e testados em `hooks-raw/` (`bash run-selftest.sh` →
37 ok, 0 falhas).

### 2.1 PreToolUse — bloquear `rm -rf` (exemplo oficial dos docs, em bash+jq)

`settings.json`:
```json
{ "hooks": { "PreToolUse": [ { "matcher": "Bash",
  "hooks": [ { "type": "command", "command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/block-rm.sh" } ] } ] } }
```
`.claude/hooks/block-rm.sh`:
```bash
#!/usr/bin/env bash
input=$(cat)
command=$(jq -r '.tool_input.command' <<<"$input")
if [[ "$command" == rm* ]]; then
  echo "Blocked: rm commands are not allowed" >&2
  exit 2   # bloqueia a chamada; o stderr chega ao Claude
fi
exit 0     # sem decisão: segue o fluxo normal de permissão
```
Versão JSON (recomendada hoje, permite `ask` e reescrever o input):
```bash
printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"%s"}}\n' "motivo"
```

### 2.2 PostToolUse — auto-format + lint

```json
{ "hooks": { "PostToolUse": [ { "matcher": "Edit|Write",
  "hooks": [
    { "type": "command", "command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/posttooluse-autoformat.sh", "async": true, "timeout": 30 },
    { "type": "command", "command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/posttooluse-lint-guard.sh", "timeout": 60 }
  ] } ] } }
```
O lint devolve `exit 2` + stderr para o Claude corrigir na mesma volta (a escrita **não**
é desfeita em PostToolUse).

### 2.3 UserPromptSubmit — injetar contexto / bloquear segredo

```bash
#!/usr/bin/env bash
input=$(cat)
prompt=$(jq -r '.prompt' <<<"$input")
if grep -qE 'AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{36}|BEGIN [A-Z ]*PRIVATE KEY' <<<"$prompt"; then
  jq -nc '{decision:"block",reason:"O prompt contém uma credencial. Use variáveis de ambiente.",suppressOriginalPrompt:true}'
  exit 0
fi
jq -nc --arg c "branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null); hora=$(date -Is)" \
  '{hookSpecificOutput:{hookEventName:"UserPromptSubmit",additionalContext:$c}}'
```

### 2.4 Notification — notificação de desktop (exemplo literal dos docs)

```json
{ "hooks": { "Notification": [ { "matcher": "",
  "hooks": [ { "type": "command", "command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/notification-desktop.sh" } ] } ] } }
```
```bash
#!/bin/bash
input=$(cat); title="Claude Code"
body=$(jq -r '.message // "Needs your attention"' <<<"$input")
seq=$(printf '\033]777;notify;%s;%s\007' "$title" "$body")
jq -nc --arg seq "$seq" '{terminalSequence: $seq}'
```
(O mesmo shape funciona para ntfy/telegram: o evento é a oportunidade, o canal é seu.)

### 2.5 Stop — gate: rodar testes antes de encerrar

```json
{ "hooks": { "Stop": [ { "hooks": [ { "type": "command",
  "command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/stop-quality-gate.sh", "timeout": 300 } ] } ] } }
```
```bash
[[ "$(jq -r '.stop_hook_active' <<<"$INPUT")" == "true" ]] && exit 0   # não entra em loop
npm test --silent > /tmp/t.out 2>&1 || jq -nc --arg r "Testes falharam:
$(tail -20 /tmp/t.out)" '{decision:"block",reason:$r}'
```
Variante sem bloqueio (feedback gentil, aparece como "Stop hook feedback"):
```bash
jq -nc '{hookSpecificOutput:{hookEventName:"Stop",additionalContext:"Rode a suíte antes de finalizar."}}'
```

### 2.6 SubagentStop — validar o relatório do subagente

```json
{ "hooks": { "SubagentStop": [ { "matcher": "reviewer", "hooks": [ { "type": "command",
  "command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/subagentstop-report-validator.sh" } ] } ] } }
```
Usa `last_assistant_message` (não o transcript) e devolve `decision:"block"` + `reason`:
o **subagente continua rodando** e recebe o motivo como próxima instrução.

### 2.7 PreCompact / PostCompact — snapshot e anti-amnésia

```json
{ "hooks": {
  "PreCompact":  [ { "matcher": "manual|auto", "hooks": [ { "type": "command", "command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/precompact-snapshot.sh" } ] } ],
  "PostCompact": [ { "matcher": "manual|auto", "hooks": [ { "type": "command", "command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/postcompact-reminder.sh" } ] } ] } }
```
PreCompact pode bloquear (exit 2); PostCompact não tem decisão nenhuma — sirva-se dele
para reinjetar “relia AGENTS.md/CLAUDE.md” (`additionalContext`).

### 2.8 SessionStart — contexto do repo na abertura

```bash
jq -nc --arg c "branch=$(git rev-parse --abbrev-ref HEAD); commits:
$(git log --oneline -5); sujo:
$(git status --porcelain | head)" \
  '{hookSpecificOutput:{hookEventName:"SessionStart",additionalContext:$c,sessionTitle:"claude:minha-branch"}}'
```
Suporta também `watchPaths`, `initialUserMessage` e `reloadSkills: true` (depois de
instalar skills, para o mesmo processo enxergá-las).

### 2.9 SessionEnd — log de encerramento (budget 1.5s)

```bash
jq -c '{ts:now,event:"SessionEnd",session_id,cwd,reason}' <<<"$INPUT" >> ~/.claude/hook-logs/sessions.jsonl
```
Sem decisão possível; mantenha curto e **sem rede**.

---

## 3. Hooks reais da comunidade (validados)

Método de validação usado em cada linha:
`gh api repos/<owner>/<repo> --jq '.stargazers_count,.pushed_at'`,
`git clone --depth 1` em `/tmp` + `find` para listar arquivos reais, e inspeção do
`hooks.json`/script. Estrelas = leitura de `gh api` em **16/09/2026**.

### 3.1 Coleções / bases de código

| Nome | Fonte | Estrelas | O que entrega | Validação |
|---|---|---|---|---|
| **claude-code-hooks-mastery** | github.com/disler/claude-code-hooks-mastery | **3921** (636 forks) | Um `.claude/hooks/*.py` para **cada evento**: `pre_tool_use.py` (bloqueia `rm -rf` + `.env`), `post_tool_use.py`, `session_start.py` (git status), `stop.py`, `subagent_stop.py`, `notification.py`, `pre_compact.py`, `permission_request.py`, `setup.py`, + `validators/ruff_validator.py` | ✅ clone real: 13 scripts em `.claude/hooks/`, `validators/{ruff,ty}_validator.py`, `settings.json` com hooks para 11 eventos |
| **claude-code-hooks** (plugins) | github.com/karanb192/claude-code-hooks | **513** | **23 plugins**: `protect-secrets`, `protect-tests`, `git-safety`, `block-dangerous-commands`, `format-code`, `config-guard`, `notify-permission`, `session-logger`, `subagent-spawn-cap`, `auto-stage`, `cache-tax`, `standup-autopilot`, ... | ✅ clone real: `plugins/<nome>/hooks/hooks.json` cada um com matcher exato |
| **awesome-claude-code-hooks** | github.com/ithiria894/awesome-claude-code-hooks | 24 | curadoria por categoria (security, safety, observability, quality gates, context, model routing, session, notification, git) com links e evento de cada hook | ✅ clone real (README.md + CONTRIBUTING.md) — **usado como fonte desta pesquisa** |
| **awesome-claude-code** | github.com/hesreallyhim/awesome-claude-code | 54171 | seção "Hooks 🪝" no diretório maior da comunidade | ✅ `gh api` |
| **ECC** (ex-`everything-claude-code`) | github.com/affaan-m/ECC | 260099 ⚠️ | 26 entradas de hook em 7 grupos, 27 scripts, presets minimal/standard/strict | ⚠️ número de estrelas implausível e repo renomeado — **marcar como NAO_VALIDADO** quanto a estrelas |
| **Multi-Agent Observability** | github.com/disler/claude-code-hooks-multi-agent-observability | **1537** | dashboard em tempo real consumindo eventos de hook do Claude Code | ✅ `gh api` |
| **Continuous Claude v3** | github.com/parcadei/Continuous-Claude-v3 | **3941** | hooks mantêm estado via ledgers/handoffs (contexto sobrevive à sessão) | ✅ `gh api` |

### 3.2 Segurança e guardrails

| Nome | Fonte | Estrelas | Evento / matcher | Comando exato | Evidência |
|---|---|---|---|---|---|
| **dwarvesf/claude-guardrails** | github.com/dwarvesf/claude-guardrails | **34** | `PreToolUse` Bash (6 regras) | `bash -c 'CMD=$(cat \| jq -r ".tool_input.command // empty"); if echo "$CMD" \| grep -qEi "rm\s+-(r\|f\|rf\|fr)\s+(/\|~\|$HOME)"; then echo "BLOCKED: ..." >&2; exit 2; fi'` | ✅ clone real: `full/settings.json`, `full/scan-secrets.sh`, `lite/settings.json`, `patterns/secrets.json` |
| ↳ regras do full | idem | — | PreToolUse Bash | push em main/master/production; pipe-to-shell (`curl … \| bash`); exfiltração (`ngrok\|burp\|webhook.site\|requestbin`); `--dangerously-skip-permissions`; `scan-commit.sh` (timeout 10) | ✅ lidas do settings.json clonado |
| ↳ scan-secrets | idem | — | `UserPromptSubmit` + `Bash` | `scan-secrets.sh` bloqueia segredos no prompt (padrões em `patterns/secrets.json`, jq/Oniguruma + detecção de seed BIP39 de 12+ palavras) | ✅ arquivo clonado (exit 2 = prompt rejeitado) |
| **lasso-security/claude-hooks** | github.com/lasso-security/claude-hooks | **265** | `PostToolUse` | `post-tool-defender.py` — varre o output de ferramentas contra 50+ padrões de prompt injection e injeta aviso no contexto | ✅ clone real: `.claude/skills/prompt-injection-defender/hooks/defender-python/post-tool-defender.py` + `patterns.yaml` |
| **rulebricks/claude-code-guardrails** | github.com/rulebricks/claude-code-guardrails | **79** | `PreToolUse` + `PostToolUse` | `guardrail.py` | ✅ `gh api` + arquivos (`install.sh`, `guardrail.py`) |
| **wangbooth/Claude-Code-Guardrails** | github.com/wangbooth/Claude-Code-Guardrails | **54** | PreToolUse/PostToolUse | branch protection + checkpoint automático + squash seguro | ✅ `gh api` |
| **liberzon/claude-hooks** | github.com/liberzon/claude-hooks | 17 | `PreToolUse` Bash | `smart_approve.py` — **decompõe comandos compostos** (`&&`, `\|\|`, `;`, `\|`, `$()`, crases, newlines) e valida cada subcomando contra allow/deny dos 3 níveis de settings | ✅ clone real: `smart_approve.py` (lido; `load_merged_settings` lê global+projeto+local) |
| **panuhorsmalahti/claude-code-permissions-hook** | idem | 2 | PreToolUse | permissões granulares em TOML, em Rust, com log de auditoria JSON | ⚠️ repo existe; script não inspecionado — **NAO_VALIDADO** |
| **CloneGuard** | github.com/prodnull/cloneguard | — | PreToolUse/PostToolUse/InstructionsLoaded | classificador ONNX não-promptável | ❌ **NAO_VALIDADO** (não pesquisado individualmente) |

### 3.3 Qualidade de código, TDD e testes

| Nome | Fonte | Evidência | Evento / matcher | Comando exato |
|---|---|---|---|---|
| **ruff/ty validators** | disler/claude-code-hooks-mastery | ✅ script clonado | `PostToolUse` `Edit\|Write` | `uv run $CLAUDE_PROJECT_DIR/.claude/hooks/validators/ruff_validator.py` → `uvx ruff check <file>` e emite `{"decision":"block","reason":...}` |
| **protect-tests** | karanb192/claude-code-hooks | ✅ `hooks.json` clonado | `PreToolUse` `Bash\|Edit\|MultiEdit\|Write` | `node "${CLAUDE_PLUGIN_ROOT}/protect-tests.js"` |
| **format-code** | idem | ✅ | `PostToolUse` `Write\|Edit` | `node "${CLAUDE_PLUGIN_ROOT}/format-code.js"` |
| **auto-stage** | idem | ✅ | `PostToolUse` `Edit\|Write` | `node "${CLAUDE_PLUGIN_ROOT}/auto-stage.js"` |
| **Claude Organizer** | github.com/ramakay/claude-organizer | 69 ⭐ | `PostToolUse` `Write` | move arquivo criado no lugar errado (scripts→`scripts/`, docs→`docs/`), preserva README/LICENSE |
| **auto-lint** | affaan-m/ECC | ⚠️ | PostToolUse Write/Edit | em `hooks/hooks.json` |

### 3.4 Notificação, observabilidade e custo

| Nome | Fonte | Evidência | Evento | Comando |
|---|---|---|---|---|
| **notify-permission** | karanb192/claude-code-hooks | ✅ `hooks.json` | `Notification`, matcher `permission_prompt\|idle_prompt\|elicitation_dialog` | `node "${CLAUDE_PLUGIN_ROOT}/notify-permission.js"` |
| **claude-notification-hook** | github.com/hqtrung/claude-notification-hook | 2 ⭐ ✅ arquivos reais | Notification/Stop/SessionStart | `notify_claude_enhanced.sh`, `session_summary_hook.py`, `interactive_notifier_enhanced.py` (Telegram com resposta interativa) |
| **claude-hooks-notifier** | github.com/shdennlin/claude-hooks-notifier | 0 ⭐, pushed 2026-03 | Notification | `scripts/claude-notification-handler.sh` + `hooks.json.example` |
| **Telegram Stop hook (gist)** | gist.github.com/g761007/d0cb319faa4f664c8918a2ac282be8c2 | ❌ **NAO_VALIDADO** | Stop | `notify-telegram.sh` (projeto, resumo, ctx%, modelo, rate limit) |
| **claude-code-ntfy-notification-hook** | pypi.org/project/claude-code-ntfy-notification-hook | ❌ **NAO_VALIDADO** | Notification | pacote pip que chama `send-ntfy-claude-notification` |
| **session-logger** | karanb192/claude-code-hooks | ✅ | SessionStart/PostToolUse(`Edit\|Write\|Bash\|Read`, async)/SessionEnd | `node "${CLAUDE_PLUGIN_ROOT}/session-logger.js"` |
| **cache-tax / cost tracker** | idem | ✅ plugin presente | PostToolUse | estimativa de custo por sessão (`utils/event-logger.py`) |
| **Model router** | github.com/tzachbon/claude-model-router-hook | 83 ⭐ | PreToolUse | troca de tier de modelo por complexidade |
| **MadameClaude** | github.com/williamkapke/MadameClaude | 25 ⭐ | PreToolUse/PostToolUse | stream de eventos para web UI |

### 3.5 Contexto, memória e sessão

| Nome | Fonte | Evidência | Evento | O que faz |
|---|---|---|---|---|
| **post_compact_reminder** | github.com/Dicklesworthstone/post_compact_reminder | 54 ⭐ | `PostCompact` | detecta compactação e manda reler AGENTS.md (anti-amnésia) |
| **Superpowers session-start** | github.com/obra/superpowers | 287594 ⭐ ⚠️ | SessionStart | carrega contexto do projeto e tasks ativas (`hooks/hooks.json`) |
| **Graft** (ex-NanoNets) | github.com/trailhq/Graft | 8260 ⭐, HN Show **39 pts / 44 comments** | hooks de busca | "cut grep tokens by 42%" |
| **claude-hook-utils** | github.com/RasmusGodske/claude-hook-utils | 31 ⭐, HN **18 pts** | biblioteca | utilitários Python para escrever hooks |
| **decider/claude-hooks** | github.com/decider/claude-hooks | 75 ⭐, HN item 44477756 (**3 pts**, 1 comment) | múltiplos | os "6 hooks" do post do HN |
| **anti-regression setup** | github.com/CreatmanCEO/claude-code-antiregression-setup | 12 ⭐, HN 4 pts | múltiplos | CLAUDE.md + subagentes + hooks anti-regressão |
| **claude-code-race** | github.com/sembsa/claude-code-race | 13 ⭐, HN 3 pts | todos | dashboard de "corrida" a partir dos eventos de hook |
| **define-claude-code-hooks** | github.com/timoconnellaus/define-claude-code-hooks | 16 ⭐, HN 3 pts | framework TS | declarar hooks em TypeScript |

### 3.6 O que NÃO conseguimos validar (diga-se de passagem)

| Alvo | Status | Motivo |
|---|---|---|
| `anthropics/claude-code/tree/main/hooks` (exemplo oficial "block `--no-verify`") | ❌ **NAO_VALIDADO** | `gh api repos/anthropics/claude-code/contents/hooks` → **404**; `raw.githubusercontent.com/.../hooks/block-no-verify.json` → **404**. O repo existe (145415 ⭐) mas o diretório citado por listas de terceiros não existe em `main` |
| Threads Reddit r/ClaudeAI (`1t53m01`, `1qlzxr1`) | ❌ **NAO_VALIDADO** | títulos aparecem na busca, mas `reddit.com/...json` e o browser retornaram "You've been blocked by network security" |
| Gists citados (telegram/ntfy) | ❌ **NAO_VALIDADO** | não inspecionados individualmente |
| `prodnull/cloneguard`, `michaelhannecke/claude-injection-guard`, `micheam/...` | ❌ **NAO_VALIDADO** | citados em listas curadas; não clonados |
| Listas de blogs (500k.io, skiln.co, devcheolu.com, danilchenko.dev, blakecrosley.com, agentrulegen, heyuan110, claudedirectory) | ⚠️ | achados por busca; conteúdo não verificado linha a linha — tratados como **pistas**, não como evidência |

> Nota de honestidade metodológica: os números de estrelas são os retornados por
> `gh api` na data da pesquisa; alguns (obra/superpowers 287k, affaan-m/ECC 260k,
> hesreallyhim 54k, trailhq/Graft 8.2k) parecem inflados para a idade dos repos e são
> reportados como lidos, não como julgados.

---

## 4. Scripts entregues em `research/hooks-raw/`

Todos funcionais, fail-open, sem segredo hardcoded (credenciais por env var:
`NTFY_TOPIC`, `NTFY_SERVER`, `NTFY_TOKEN`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`,
`CLAUDE_HOOK_LOG_DIR`, `COMMIT_REGEX`, `SUBAGENT_REQUIRED_SECTIONS`, `CLAUDE_EXTRA_DENY`).

| Script | Evento | Matcher | Linguagem | Decisão |
|---|---|---|---|---|
| `pretooluse-block-dangerous-bash.sh` | PreToolUse | Bash | bash+jq | deny (7 famílias de regra) |
| `pretooluse-protect-secrets.sh` | PreToolUse | Read\|Edit\|Write\|MultiEdit\|Bash | bash+jq | deny (.env, chaves, credenciais, wallet; ignora `.env.example`) |
| `pretooluse-git-safety.sh` | PreToolUse | Bash | bash+jq | deny (push main, force-push, `--no-verify`, reset --hard, autoria falsa) |
| `pretooluse-tdd-guard.sh` | PreToolUse | Edit\|Write\|MultiEdit\|Bash | bash+jq | deny (skip/assert fraco/apagar teste) |
| `pretooluse-commit-message-lint.sh` | PreToolUse | Bash + `if: Bash(git commit *)` | bash+jq | deny (Conventional Commits, subject ≤72, sem "co-authored-by: claude") |
| `pretooluse-compound-bash-guard.py` | PreToolUse | Bash | python3 | deny (decompõe `&& \|\| ; \| $() \` \n`) |
| `posttooluse-autoformat.sh` | PostToolUse | Edit\|Write\|MultiEdit | bash | async, 13 linguagens |
| `posttooluse-lint-guard.sh` | PostToolUse | Edit\|Write\|MultiEdit | bash | exit 2 → Claude corrige |
| `posttooluse-typecheck-ts.sh` | PostToolUse | Edit\|Write\|MultiEdit | bash | exit 2 com erros do `tsc --noEmit` |
| `posttooluse-test-runner.sh` | PostToolUse | Edit\|Write\|MultiEdit | bash | exit 2 com teste relacionado |
| `posttooluse-log-toolcalls.py` | PostToolUse | (todos) | python3 | async, JSONL com redação de conteúdo |
| `posttooluse-injection-guard.sh` | PostToolUse | WebFetch\|WebSearch\|Read\|Bash | bash+jq | aviso ao Claude (10 famílias de padrão) |
| `userpromptsubmit-context-inject.sh` | UserPromptSubmit | — | bash+jq | block se achar credencial; senão contexto |
| `sessionstart-context-inject.sh` | SessionStart | startup\|resume\|clear\|fork | bash+jq | additionalContext + sessionTitle |
| `notification-desktop.sh` | Notification | permission_prompt\|idle_prompt\|elicitation_dialog | bash+jq | `terminalSequence` (OSC 777) |
| `stop-notify-ntfy.sh` | Stop/Notification | — | bash+curl | push ntfy |
| `stop-notify-telegram.sh` | Stop | — | bash+curl | push Telegram |
| `stop-quality-gate.sh` | Stop | — | bash+jq | block com anti-loop (`stop_hook_active` + contador ≤3) |
| `stop-cost-tracking.py` | Stop | — | python3 | lê `transcript_path`, estima custo, grava CSV |
| `subagentstop-report-validator.sh` | SubagentStop | nome do agente | bash+jq | block até o relatório cumprir contrato |
| `precompact-snapshot.sh` | PreCompact | manual\|auto | bash+git | snapshot do estado em `.claude/session-state/` |
| `postcompact-reminder.sh` | PostCompact | manual\|auto | bash+jq | reinjeta regras + último snapshot |
| `sessionend-log.sh` | SessionEnd | — | bash+jq | log + limpeza (≤1.5s) |
| `settings.example.json` | — | — | JSON | configuração completa dos 11 eventos |
| `run-selftest.sh` | — | — | bash | **37 testes, 37 ok, 0 falhas** |

Verificação executada:

```
$ cd research/hooks-raw && bash run-selftest.sh
...
== 37 ok, 0 falhas ==
```

---

## 5. TOP 12 hooks

| # | Evento | O que faz | Por que vale | Origem |
|---|---|---|---|---|
| 1 | `PreToolUse` (Bash) | **Bloqueia comando destrutivo** (`rm -rf /`, `mkfs`, `dd of=/dev/`, fork bomb, pipe-to-shell) | Única barreira antes do dano; erro de operação custa caro, hook custa 5s | dwarvesf/claude-guardrails + disler/claude-code-hooks-mastery + docs oficiais |
| 2 | `PreToolUse` (Read\|Edit\|Write\|Bash) | **Protege `.env`, chaves SSH, credenciais, wallets** | Vazamento de segredo é irreversível; bloqueio de leitura vale mais que o de escrita | karanb192/protect-secrets, disler `pre_tool_use.py`, dwarvesf `permissions.deny` |
| 3 | `PreToolUse` (Bash) | **Git safety** — push em main, force-push, `--no-verify`, `reset --hard` | Salva histórico compartilhado e evita reescrever/forçar trabalho dos outros | dwarvesf (push protegido), karanb192/git-safety |
| 4 | `PreToolUse` (Bash) | **Decompor comandos compostos** e negar por subcomando | Fecha o furo "`npm test && rm -rf /`"; regex simples não vê o segundo comando | liberzon/claude-hooks `smart_approve.py` |
| 5 | `PostToolUse` (Edit\|Write) | **Auto-format** (prettier/ruff/black/gofmt/…) | Elimina ruído de formatação dos diffs, deixa o agente "invisível" para o time | karanb192/format-code, tutoriais de auto-format |
| 6 | `PostToolUse` (Edit\|Write) | **Lint + typecheck** que devolve erro ao Claude (`exit 2`) | Fecha o loop dentro do turno; o modelo corrige em vez de você revisar | disler `validators/ruff_validator.py` + `ty_validator.py` |
| 7 | `PostToolUse` (Edit\|Write) | **Rodar os testes relacionados** ao arquivo editado | Detecta regressão na hora, no contexto exato da mudança | docs oficiais (seção de testes com hooks) + tutoriais de quality gate |
| 8 | `Stop` | **Gate de conclusão**: suíte falhou → `decision:"block"` e o agente continua | Impede "terminou" com build vermelho; usar `stop_hook_active` + cap de 8 | docs oficiais (Stop decision control), TDD gate da comunidade |
| 9 | `PreToolUse` (Edit\|Write\|Bash) | **TDD guard**: impede `skip`, `assert True` ou apagar teste para passar | Preserva o valor dos testes como especificação; único hook que evita auto-engano | karanb192/protect-tests + affaan-m/ECC |
| 10 | `PostToolUse` (WebFetch\|Read\|Bash) | **Scan de prompt injection** na saída das ferramentas | Ataque não vem do seu prompt, vem do conteúdo que a ferramenta leu | lasso-security/claude-hooks (265 ⭐), dwarvesf prompt-injection-defender |
| 11 | `Stop` / `Notification` | **Notificação** (ntfy/Telegram/desktop via `terminalSequence`) | Trabalho assíncrono sem ficar olhando a tela; `idle_prompt`/`permission_prompt` alertam na hora certa | karanb192/notify-permission, hqtrung/claude-notification-hook, gist Telegram, docs oficiais |
| 12 | `PreCompact` + `PostCompact` | **Snapshot antes** + **reinjeta AGENTS.md/CLAUDE.md depois** | Cura a "amnésia pós-compactação" em sessões longas | Dicklesworthstone/post_compact_reminder (54 ⭐), parcadei/Continuous-Claude-v3 |

Menções honrosas: `sessionstart-context-inject.sh` (branch/commits/comando de teste no
início), `posttooluse-log-toolcalls.py` + `stop-cost-tracking.py` (observabilidade e custo),
`pretooluse-commit-message-lint.sh` (Conventional Commits), `subagentstop-report-validator.sh`
(contrato de relatório de subagente).

---

## 6. Regras para não se queimar

1. **Use exit 2 só para bloquear.** Em PostToolUse ele é *feedback*; `exit 1` nunca bloqueia.
2. **Fail-open é obrigatório** em hook que roda em todo tool call: dependência ausente → `exit 0`.
3. **PreToolUse usa `hookSpecificOutput.permissionDecision`**, não `decision` no topo (depreciado).
4. **Deny no hook ≠ política dura.** `if` e matcher são best-effort; para garantia use
   `permissions.deny` além do hook.
5. **Timeout em PreToolUse não protege** — hook cancelado simplesmente não decide.
6. **Stop sem anti-loop** vira loop infinito (existe cap de 8, mas gaste tokens à toa).
7. **`if`** economiza processo (`"if": "Bash(git commit *)"`, `"if": "Edit(*.ts)"`), separe
   condições em handlers distintos (não há `&&`/`||`).
8. **Nunca `/dev/tty`** — use `terminalSequence`.
9. **Hooks rodam em paralelo**; a mesma entrada em vários settings roda uma vez só.
10. **`async: true`** para formatar/logar/notificar; **síncrono** só quando a decisão
    precisa chegar antes da próxima request.

## 7. Fontes

- Docs oficiais: `code.claude.com/docs/en/hooks` (referência) e `…/hooks-guide` (guia).
- Repos clonados e inspecionados em `/tmp`: disler/claude-code-hooks-mastery,
  ithiria894/awesome-claude-code-hooks, karanb192/claude-code-hooks,
  dwarvesf/claude-guardrails, lasso-security/claude-hooks, rulebricks/claude-code-guardrails,
  liberzon/claude-hooks, hqtrung/claude-notification-hook, shdennlin/claude-hooks-notifier.
- `gh api` (estrelas/última atividade) para 25 repos listados na seção 3.
- Hacker News (Algolia + Firebase): itens 44477756, 47678197, 48318978, 48211487.
- Busca web: awesome-claude-code (hesreallyhim), claude.com/blog/how-to-configure-hooks,
  e blogs de hooks usados apenas como pistas (marcados na seção 3.6).
