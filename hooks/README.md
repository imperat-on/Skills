# Hooks

Política de guarda e observabilidade para agentes de código, escrita **uma vez**
e usada em várias CLIs. Os seis scripts de `scripts/` seguem o contrato que
Claude Code, Codex, Cursor e Hermes aceitam sem adaptação:

```
JSON do evento no stdin  →  script decide  →  exit 0 = libera
                                              exit 2 = BLOQUEIA (motivo no stderr)
```

`exit 2` é a menor superfície comum: está documentado como bloqueio no Claude
Code, no Codex (`developers.openai.com/codex/hooks`) e no Hermes
(`agent/shell_hooks.py`, que também aceita `{"decision":"block","reason":...}`).
Um arquivo funciona nas quatro CLIs — sem plugin, sem SDK, sem jq.

## A matriz evento × CLI

| O que queremos | Claude Code | Codex CLI | Hermes Agent | OpenCode | Prime Agent |
|---|---|---|---|---|---|
| antes de ferramenta | `PreToolUse` | `PreToolUse` (`Bash`, `apply_patch`) | `pre_tool_call` / `post_tool_call` | `tool.execute.before` (plugin JS) | `tool_call` (extension TS) |
| depois de ferramenta | `PostToolUse` | `PostToolUse` | `post_tool_call` | `tool.execute.after` | `tool_result` |
| início de sessão | `SessionStart` | `SessionStart`, `SubagentStart` | `on_session_start` | evento `session.created` | `session_start` |
| fim de turno | `Stop` | `Stop`, `SubagentStop` | `post_llm_call` | evento `session.idle` | sem equivalente direto (`session_shutdown` é fim de sessão) |
| como bloquear | exit 2 ou `permissionDecision: deny` | exit 2 ou `{"decision":"block"}` | exit 2 ou `{"action":"block"}` | `throw` dentro do `tool.execute.before` | `return { block: true, reason }` |
| onde se declara | `~/.claude/settings.json` | `~/.codex/hooks.json` | `hooks:` em `~/.hermes/config.yaml` | `~/.config/opencode/plugins/*.js` | `~/.prime/agent/extensions/*.ts` |
| confiança | diretório já confiado | **exige `/hooks` para confiar (hash)** | consentimento por `(evento, comando)` | código local é confiado | código local é confiado |

Codex merece o aviso: ele guarda o hash da definição do hook e **não roda** até
você revisar em `/hooks`. Depois de qualquer edição nos scripts, revise de novo.

## Os seis scripts

| Arquivo | Evento | Bloqueia? | O que faz |
|---|---|---|---|
| `guard-dangerous.py` | pre-tool | sim | comandos destrutivos (lista abaixo) |
| `guard-secrets.py` | pre-tool | sim | credenciais em arquivo, em patch e na linha de comando |
| `auto-format.sh` | post-tool | não | formata o arquivo tocado, usando o formatador do projeto |
| `audit-log.sh` | post-tool | não | linha JSONL por chamada, com redação de token |
| `session-context.sh` | session start | não | injeta branch, dirty files e últimos commits |
| `notify-stop.sh` | stop | não | toast no desktop (+ ntfy/webhook, se configurado) |

### O que `guard-dangerous.py` bloqueia

`rm -rf` na raiz, no `$HOME`, em `.`/`*` e em **qualquer caminho absoluto fora de
`/tmp`** · `sudo rm -rf` · `mkfs`/`wipefs`/`sudo parted` · `dd of=/dev/sdX` · `> /dev/sdX` ·
`chmod -R 777 /` · fork bomb · `shutdown`/`reboot` · `git push --force` / `-f`
(`--force-with-lease` **passa**) · `git commit --no-verify` · `git clean -fdx` ·
`git reset --hard` · `git checkout/restore .` · `git branch -D` · `git filter-branch` ·
`curl|wget | sh` e `| python` · `DROP`/`TRUNCATE` · `DELETE FROM` sem `WHERE` ·
`FLUSHALL` · `kubectl delete` de recurso · `terraform destroy` /
`apply -auto-approve` · `docker prune -a` · `passwd`/`>` em `/etc/passwd` · `crontab -r` · `history -c`

Passa de propósito: `rm -rf node_modules`, `rm -rf /tmp/build`, `rm ./x.log`,
`grep "rm -rf"` e `echo "cuidado com rm -rf /"`.

### O que `guard-secrets.py` bloqueia

`.env` e `.env.*` (mas `.env.example`, `.env.sample`, `.env.template`, `.env.dist`
passam) · `id_rsa`/`id_ed25519` · `*.pem`, `*.key`, `*.p12`, `*.pfx`, `*.jks` ·
qualquer coisa sob `~/.ssh/`, `~/.aws/`, `~/.gnupg/`, `~/.docker/`, `~/.kube/`,
`~/.config/gh/`, `~/.config/gcloud/` · `credentials.json`, `serviceAccount*.json`,
`secrets.{json,yaml,yml}` · leitura via shell (`cat .env`, `grep … .env`) ·
escrita via shell (`> .env`) · `gh auth token`, `aws configure get`,
`gcloud auth print-access-token`, `op item get` · `git add .env` · `cp`/`scp`/`curl`
de `~/.ssh` ou `.env` · chave privada, `AKIA…`, `sk-…`, `ghp_…`, `xox…`, JWT e
`Authorization: Bearer …` **gravados** em arquivo ou colados na linha de comando.

Cobre também o Codex: quando o edit chega como `apply_patch`, os caminhos são
extraídos de `*** Add/Update/Delete File:` e checados um por um.

## Instalar

```bash
./install-hooks.sh                 # nas CLIs detectadas, com backup do config
./install-hooks.sh --dry-run       # só mostra
./install-hooks.sh --only codex    # claude|codex|hermes|opencode|prime|cursor
```

- **Claude Code** — faz *merge* em `~/.claude/settings.json` (não sobrescreve hooks que já existem) e cria `.bak-<timestamp>`.
- **Codex** — escreve `~/.codex/hooks.json` (backup do anterior). Depois abra `/hooks` e confie.
- **Hermes** — anexa o bloco `hooks:` em `~/.hermes/config.yaml` **só se não existir um** (se existir, ele mostra o trecho e não toca). Valide com `hermes hooks test`.
- **OpenCode / Prime Agent** — copiam um plugin/extensão que apenas chama os mesmos scripts Python (a política continua num lugar só). Reinicie a CLI / rode `/reload`.
- **Cursor** — escreve `~/.cursor/hooks.json`. **Único schema não conferido na doc oficial** (veio de `affaan-m/ECC`, MIT). Teste antes de confiar.

Nada é instalado sem o arquivo de config original ser copiado antes.

## Testar

```bash
bash ../tools/test-hooks.sh
```

52 casos com payload real de Claude Code, Codex (incluindo `apply_patch`) e
Hermes, sem depender de nenhuma CLI: cada linha de `guard-dangerous`/`guard-secrets`
tem um caso de bloqueio **e** um caso de permissão, para pegar falso positivo —
que é o modo de falha que importa.

## Falhar aberto ou fechado

Os guards são instalados com `fail_closed: true` só no Hermes
(`hooks:` em `config.yaml`), onde existe essa opção explícita. Nos outros, um
script que quebra é apenas registrado e a ação segue — por isso o
`guard-dangerous.py`/`guard-secrets.py` não têm dependência externa além de
Python 3 e tratam payload malformado como "não é da minha conta".

Troca consciente: prefiro que um guard quebrado logue um erro a travar a sessão
inteira do usuário. Se você quiser o contrário no Claude Code, troque o
`exit 0` dos scripts por `exit 2` na exceção (e assuma o risco de travar por bug).

## Privacidade do log de auditoria

`audit-log.sh` escreve em `${XDG_STATE_HOME:-~/.local/state}/skills-kit/audit.jsonl`.
Ele registra evento, ferramenta, cwd, sessão, **nomes** das chaves de input e um
resumo do alvo — com redação de token (`sk-`, `ghp_`, `AKIA…`, `Bearer …`,
`token=…`). Mesmo assim: se você colar um segredo no chat, ele pode acabar no alvo
do comando antes da redação. Trate o arquivo como dado sensível.

## community/

`community/` traz 26 hooks extras coletados na pesquisa (notificação por
ntfy/Telegram, lint/typecheck no post-tool, TDD guard, cost tracking,
`PreCompact` snapshot…). Eles têm **selftest próprio** (`bash community/run-selftest.sh`
— 37 casos, todos passando quando foram escritos), mas **não** passaram pelos 52
casos deste kit, e vários dependem de `jq` (que você tem em `/usr/bin/jq`). Use
como referência ou copie um de cada vez — o lugar de confiar é `scripts/`.
