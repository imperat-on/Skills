# hooks-raw — scripts de hook prontos para usar (Claude Code)

Cada script recebe o JSON do evento **no stdin** e responde por **exit code** + **stdout/JSON**.
Nenhum segredo fica hardcoded: credenciais vêm de variáveis de ambiente (`NTFY_TOPIC`,
`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `HOOK_SAFETY_LEVEL`, ...).

Instalação rápida:

```bash
mkdir -p .claude/hooks && cp hooks-raw/*.{sh,py} .claude/hooks/ && chmod +x .claude/hooks/*
# depois copie o bloco "hooks" de settings.example.json para .claude/settings.json
```

Teste unitário (fora do Claude Code):

```bash
echo '{"tool_name":"Bash","tool_input":{"command":"rm -rf /"}}' | ./pretooluse-block-dangerous-bash.sh
```

## Índice

| Script | Evento | Matcher | Linguagem | Bloqueia? |
|---|---|---|---|---|
| pretooluse-block-dangerous-bash.sh | PreToolUse | Bash | bash+jq | sim (deny) |
| pretooluse-protect-secrets.sh | PreToolUse | Read\|Edit\|Write\|MultiEdit\|Bash | bash+jq | sim (deny) |
| pretooluse-git-safety.sh | PreToolUse | Bash | bash+jq | sim (deny) |
| pretooluse-tdd-guard.sh | PreToolUse | Edit\|Write\|MultiEdit\|Bash | bash+jq | sim (deny) |
| pretooluse-commit-message-lint.sh | PreToolUse | Bash (if `Bash(git commit *)`) | bash+jq | sim (deny) |
| pretooluse-compound-bash-guard.py | PreToolUse | Bash | python3 | sim (deny) |
| posttooluse-autoformat.sh | PostToolUse | Edit\|Write\|MultiEdit | bash+jq | não (async) |
| posttooluse-lint-guard.sh | PostToolUse | Edit\|Write\|MultiEdit | bash+jq | feedback (exit 2) |
| posttooluse-typecheck-ts.sh | PostToolUse | Edit\|Write\|MultiEdit | bash+jq | feedback (exit 2) |
| posttooluse-test-runner.sh | PostToolUse | Edit\|Write\|MultiEdit | bash+jq | feedback (exit 2) |
| posttooluse-log-toolcalls.py | PostToolUse | (todos) | python3 | não (async) |
| posttooluse-injection-guard.sh | PostToolUse | WebFetch\|WebSearch\|Read\|Bash | bash+jq | aviso ao Claude |
| userpromptsubmit-context-inject.sh | UserPromptSubmit | — | bash+jq | só com segredo no prompt |
| sessionstart-context-inject.sh | SessionStart | startup\|resume\|clear\|fork | bash+jq | não |
| notification-desktop.sh | Notification | permission_prompt\|idle_prompt\|elicitation_dialog | bash+jq | não |
| stop-notify-ntfy.sh | Stop / Notification | — | bash+jq+curl | não |
| stop-notify-telegram.sh | Stop | — | bash+jq+curl | não |
| stop-quality-gate.sh | Stop | — | bash+jq | sim (block) |
| stop-cost-tracking.py | Stop | — | python3 | não |
| subagentstop-report-validator.sh | SubagentStop | nome do agente | bash+jq | sim (block) |
| precompact-snapshot.sh | PreCompact | manual\|auto | bash+jq+git | não |
| postcompact-reminder.sh | PostCompact | manual\|auto | bash+jq | não |
| sessionend-log.sh | SessionEnd | — | bash+jq | não |

## Regras de projeto que valem a pena

1. **Fail-open**: todo script sai 0 quando falta dependência (`jq`, linter, `tsc`) — um hook
   quebrado não pode travar a sessão. Exceto quando o objetivo explícito é bloquear.
2. **Exit 2 só existe para bloquear** em PreToolUse / UserPromptSubmit / Stop / SubagentStop /
   PreCompact. Em PostToolUse ele apenas mostra o stderr ao Claude (a ferramenta já rodou).
3. **PreToolUse usa `hookSpecificOutput.permissionDecision`** (`allow|deny|ask|defer`).
   Os campos top-level `decision`/`reason` estão depreciados nesse evento.
4. **Precedência** entre hooks que decidem o mesmo PreToolUse: `deny > defer > ask > allow`.
5. **Timeout não bloqueia** em PreToolUse: hook que estoura o tempo não impede a execução.
6. **`if`** (`"if": "Bash(git commit *)"`, `"if": "Edit(*.ts)"`) filtra por regra de permissão
   e evita gastar processo — mas é best-effort; para política dura use `permissions.deny`.
7. **Stop**: proteja-se contra loop com `stop_hook_active` e um contador por sessão
   (o Claude Code desiste sozinho após 8 bloqueios consecutivos).
8. **SessionEnd** tem budget de 1.5s (subir com `CLAUDE_CODE_SESSIONEND_HOOKS_TIMEOUT_MS`).
9. **Nunca escreva em `/dev/tty`**: notificações de terminal vão no campo `terminalSequence`.
