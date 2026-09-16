# Worker execution mode

`worker_execution_mode` decides **how every worker CLI the orchestrator starts is launched**. It is
independent of `coordination_mode` and `team_mode`.

```yaml
worker_execution_mode: autonomous | interactive    # default: autonomous
```

- `autonomous` - launch every worker in the highest-permission autonomous / non-interactive mode that
  that CLI officially supports for the run's authorized environment, so normal in-scope operations do
  not stop the workflow with confirmation prompts.
- `interactive` - launch the CLI with its default prompts (useful when the user explicitly wants to
  watch and approve each worker action).

## What `autonomous` covers - and what it never covers

Inside the **authorized scope of the run**, autonomy covers ordinary worker operations:
reading/writing/creating/editing/removing files belonging to the task; running commands; installing
local dependencies the task needs; builds; tests; lint/format; `git add`; `git commit`; and normal
operations inside the task's own worktree.

`autonomous` **never** authorizes, by itself:

- credentials, tokens or accounts that were not provided by the user;
- destructive operations outside the project / task worktree;
- touching other projects or other checkouts;
- changing resources that do not belong to this run (other panes, workspaces, worktrees, services);
- global system changes that the task does not require;
- bypassing the ownership ledger or closing/deleting anything this run did not create;
- `push`, publish, deploy, release or any external side effect that was not requested;
- answering a trust prompt, hook-trust request, credential request or sudo prompt on the user's behalf.

Autonomy removes repeated confirmations; it does not remove scope and ownership limits. The escalation
triggers in `references/coordination-modes.md` still apply to every worker in every mode.

## Discovery: never invent flags

Before starting a kind for the first time in a run, determine its official autonomous invocation from
this host, in this order:

1. `herdr agent start --help` and `herdr agent` (how Herdr forwards extra arguments: `-- <args>`);
2. the CLI's own help: `<cli> --help`, and the help of the subcommand you intend to use
   (`<cli> <subcmd> --help`);
3. documentation shipped locally (man pages, `--help` of nested commands, bundled docs);
4. the installed configuration (which may already deny or allow things the flag does not override);
5. an installed official skill/doc for that CLI (`hermes skills list`) if one exists.

Rules:

- Record the discovered command **and its observed output** before relying on it; a flag quoted from
  memory is not evidence.
- If the CLI offers no official autonomous/non-interactive mode, use the most autonomous configuration
  it officially supports (for example a non-interactive/print mode plus an explicit allow-list), record
  the limitation in `decisions.md`, and say so in the report. Never invent a bypass.
- Never use a trust-bypass flag (`--trust-repository`, hook trust, credential helpers) as a shortcut to
  make a worker stop prompting: those are user decisions.
- Flags discovered for one kind are never assumed to exist for another.

## Verified invocations on this host

Discovery performed on this machine (Herdr 0.9.0). Re-verify per run: the installed binary is the
authority, and versions change.

| kind | official autonomous invocation | evidence |
|---|---|---|
| `opencode` | `opencode --auto` | `opencode --help`: "`--auto` auto-approve permissions that are not explicitly denied (dangerous!)"; also accepted by `opencode run` |
| `codex` | `codex -a never -s workspace-write` (narrower) or `codex --dangerously-bypass-approvals-and-sandbox` (only in an externally sandboxed environment) | `codex --help`: `-a/--ask-for-approval <on-request\|never>`, `-s/--sandbox <read-only\|workspace-write\|danger-full-access>`, `--dangerously-bypass-approvals-and-sandbox`. No `--full-auto` in this version |
| `claude` | `claude --permission-mode bypassPermissions` (or `--dangerously-skip-permissions`; `--permission-mode acceptEdits` is the narrower choice, `--allowedTools` scopes further) | `claude --help`: `--permission-mode <acceptEdits\|auto\|bypassPermissions\|manual\|dontAsk\|plan>`, `--dangerously-skip-permissions`, `--allow-dangerously-skip-permissions` |
| `hermes` | `hermes --yolo` for command approvals; `--accept-hooks` only with explicit authorization | `hermes --help`: `--yolo` "Bypass all dangerous command approval prompts", `--accept-hooks` "Auto-approve any unseen shell hooks" |

Live confirmation performed for `opencode` on this host: started with
`herdr agent start <name> --kind opencode --pane <pane> -- --auto`, then given a task that wrote a file
**outside** its cwd and ran a shell command. It completed with no permission dialog and never entered
`blocked` (state went `working` -> `done`). Without `--auto`, the same class of operation had parked a
worker at an "access external directory" dialog.

Note on configuration: `opencode --auto` approves permissions that are *not explicitly denied*, so an
installed deny rule still parks the worker (config: `~/.config/opencode/opencode.json[c]`). Inspect the
configuration during discovery and record what it denies. `codex` keeps its approval policy and sandbox
in `~/.codex/config.toml`; explicit CLI flags override it.

## The engine is part of the state

A worker is a *(kind, model, launch mode)* triple, and the model belongs in the run state next to the
kind (`--launch-arg=--model`, kept in `worker_execution`). An engine that cannot finish a task is a
recovery case, not a mystery; when a worker shows visible output and no file change for a long stretch
(watchdog `spinning`), escalate deliberately:

1. narrow the contract to ONE deliverable and re-prompt the same worker;
2. if it spins again, replace the worker with a stronger model and hand it the reconstructed package
   (`orch.py replace-worker --agent <new> --old-agent <old> --reason "..."`).

Do not spend a second budget on the engine that already burned one, and never leave the model choice
implicit: a run whose worker model is unrecorded cannot be recovered on purpose.

## Post-spawn verification (required)

Autonomy that is only assumed is a trap: an interactive worker will park at a permission dialog and the
orchestrator must never answer it. After every `agent start`, confirm the observed process before
delegating:

```bash
herdr agent start <name> --kind <kind> --pane <pane> -- <autonomous-args>   # prints .result.argv
herdr pane process-info --pane <pane>   # foreground_processes[].argv — the independent check
herdr pane get <pane> && herdr agent get <name>   # cwd / foreground_cwd still correct
```

Record it on the task:

```bash
python3 scripts/orch.py set-task --id <task> --launch-mode autonomous \
  --launch-kind opencode --launch-arg --auto --launch-verified 1
```

If the observed argv lacks the intended autonomous argument, or the worker still reports `blocked` on a
routine permission dialog, fix the launch (or the placement) before sending mutating work. A worker that
never becomes ready because the guard's environment was rejected by the binary version is the same class
of bug: drop that environment, relaunch, and record `prevention: none` instead of answering anything. If a dialog
still appears, classify it: routine in-scope permission -> a launch-configuration bug, relaunch
properly; trust/credential/destructive/out-of-scope -> user decision, ask.

## Statuses

`working`, `done` and `idle` mean the same as always. `blocked` remains a decision point: with a correct
autonomous launch it should be rare, and when it happens it is either a misconfiguration (relaunch) or a
real escalation (ask the user).
