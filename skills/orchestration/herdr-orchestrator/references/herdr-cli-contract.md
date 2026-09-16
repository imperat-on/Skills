# Herdr CLI contract (verified against herdr 0.9.0, protocol 22)

The installed binary is the authority. Start every session with `herdr --skill`, then print a command
group bare (`herdr agent`, `herdr pane`, `herdr worktree`, `herdr workspace`) to see current options.
Never run bare `herdr` (it launches/attaches the TUI) and never probe a mutating command by omitting
arguments — `herdr workspace create` executes with defaults.

Verified with `herdr api schema` (JSON-RPC request/response shapes) and live calls on a running
server. When a later version changes a flag, keep the behavioral intent and use the new contract.

## Environment and reachability

```bash
test "${HERDR_ENV:-}" = 1          # official gate: are we inside a Herdr-managed pane?
herdr status                        # client + server version, protocol, socket path
printf '%s\n' "$HERDR_WORKSPACE_ID" "$HERDR_TAB_ID" "$HERDR_PANE_ID"   # caller context
```

Herdr injects the caller's context into each managed pane. `HERDR_ENV=1` is the official check; if it
is unset, do not silently drive the focused session — report it and confirm with the user (harness
wrappers can strip the variable while the socket still answers, and the focused pane may belong to
someone else). Prefer `--current`, explicit IDs or a unique agent name over the UI-focused target.

CLI exit codes: server errors are JSON on stderr with status 1; CLI syntax errors exit 2.

## IDs

- workspace `w1`, tab `w1:t1`, pane `w1:p1` — opaque, stable, per server.
- Closed tab/pane IDs are never reused. A pane moved to another workspace gets a new qualified ID
  (`.result.move_result.pane.pane_id`).
- Agent commands accept either a unique live agent name or the pane ID hosting it (not terminal IDs,
  not kind labels). Names match `[a-z][a-z0-9_-]{0,31}` and are unique among live agents; a name
  follows the current pane occupant and is cleared when that agent exits.
- IDs and names are scoped to one server. With `--remote`/saved machines, rediscover IDs on the
  target host; selecting a machine in the TUI does not retarget your commands.
- Parse IDs from JSON responses. `herdr worktree create` returns
  `.result.workspace.workspace_id`, `.result.tab.tab_id`, `.result.root_pane.pane_id`,
  `.result.worktree.path` (response `type: worktree_created`).

## Agent commands (`herdr agent`)

```
herdr agent list
herdr agent get <target>
herdr agent read <target> [--source visible|recent|recent-unwrapped|detection] [--lines N] [--format text|ansi]
herdr agent send-keys <target> <key> [key ...]        # e.g. esc, ctrl+c; all keys validated before writing
herdr agent prompt <target> <text> [--wait] [--until STATUS]... [--timeout MS]
herdr agent rename <target> <name>|--clear
herdr agent focus <target>
herdr agent wait <target> [--until STATUS]... [--timeout MS]
herdr agent attach <target> [--takeover]
herdr agent start <name> --kind KIND --pane ID [--timeout MS] [-- <agent-args...>]
herdr agent explain <target> [--json|--format text|json] [--verbose]
```

Kinds accepted by `--kind` in 0.9.0 (inspect `herdr agent` on the host instead of trusting this
list): pi, claude, codex, gemini, cursor, devin, agy, cline, omp, mastracode, opencode, copilot,
kimi, kiro, droid, amp, grok, hermes, kilo, qodercli, qwen, maki, muse.

Live `agent_list` entry shape (real output):

```json
{"id":"cli:agent:list","result":{"type":"agent_list","agents":[
  {"agent":"opencode","name":"frontend_worker","agent_status":"idle","pane_id":"w3:p1",
   "workspace_id":"w3","tab_id":"w3:t1","cwd":"/tmp/repo-frontend",
   "foreground_cwd":"/tmp/repo-frontend","interactive_ready":true,"focused":false,
   "revision":4,"state_change_seq":49,"terminal_id":"term_abc","terminal_title":"OC | ...",
   "agent_session":{"agent":"opencode","kind":"id","source":"herdr:opencode","value":"ses_..."}}
]}}
```

`herdr agent get <target>` returns the same object under `.result.agent`; `herdr pane get <pane_id>`
returns `.result.pane` with the same `cwd`/`foreground_cwd`/`agent_status` fields plus `scroll` info.
Cross-check both before delegating.

### start

`agent start` requires an **existing available shell pane** (at its interactive prompt, shell in the
foreground, nothing else running) and never creates, splits or moves layout. Use `pane split` first.
A successful start returns only after Herdr detects the expected agent in that pane and considers it
ready for interactive input. If the agent is blocked during startup the command returns
`agent_not_ready` immediately but keeps the name usable for `read`/`send-keys`. Default startup
timeout is 30 s. Wait until the agent is idle before prompting.

### prompt

`agent prompt` honors the pane's live bracketed-paste mode and sends text plus encoded Enter as one
ordered submission; success proves submission, not that a turn started. It refuses a target already
waiting at an approval/question dialog with `agent_blocked` **before sending any input**.

With `--wait`, a prompt sent from a non-working state must produce observed `working`/`blocked`
activity within ~5 s, else `agent_prompt_stalled`; the caller `--timeout` (which includes submission
time) can also expire first. The wait tracks lifecycle state, not an individual turn. Use `--until`
only for a state-specific workflow (e.g. waiting on an already-running agent to ask for input).

### Reading output

- `visible` — current viewport; `recent` — recent rendered output incl. soft wraps;
  `recent-unwrapped` — wraps joined, best for logs/transcripts; `detection` — plain-text bottom
  snapshot used for agent detection (good for TUI panes full of escapes).
- `--format ansi` only when styling is evidence. `--lines` asks for more rows from screen + host
  scrollback; if more lines reveal nothing, the agent is likely on the terminal's alternate screen —
  then ask it to write its full response to a file and read that file.

### State semantics

`working` = actively processing. `blocked` = Herdr recognized an approval/question UI (a decision
point, never completion). `done` and `idle` both mean ready for input; the server's seen-state and
each TUI client's badge can differ. `unknown` = an agent is present but unclassifiable — it does not
prove completion. Use `agent explain` when a classification is unclear.

## Worktree commands (`herdr worktree`)

```
herdr worktree list [--workspace ID | --cwd PATH] [--trust-repository]
herdr worktree create [--workspace ID | --cwd PATH] [--branch NAME] [--base REF] [--path PATH]
                      [--label TEXT] [--focus] [--no-focus] [--trust-repository]
herdr worktree open (--path PATH | --branch NAME) [--workspace ID | --cwd PATH] [--label TEXT] ...[--trust-repository]
herdr worktree remove --workspace ID [--force] [--trust-repository]
```

- `create` returns `worktree_created` with `workspace`, `tab`, `root_pane`, `worktree`.
- `open` returns `worktree_opened` with the same plus `already_open`.
- `remove` takes the **workspace ID** (not a path) and returns `worktree_removed` with
  `workspace_id`, `path`, `forced`. It is a destructive step: only for worktrees this run created,
  after their branch is integrated or intentionally abandoned and the worktree has no uncommitted
  changes.
- `list --cwd PATH` returns `.result.source` (`repo_root`, `repo_name`, `repo_key`,
  `source_checkout_path`, `source_workspace_id`) and `.result.worktrees[]` with
  `path`, `branch`, `label`, `open_workspace_id`, `is_linked_worktree`, `is_detached`, `is_bare`,
  `is_prunable`.
- `--trust-repository` grants per-request Git trust. Use it only after the user has verified that
  repository; it is not a routine retry after a failed worktree command.

## Workspace, tab, pane

```
herdr workspace list | get <id> | rename <id> <label> | focus <id> | close <id> [--group]
herdr workspace create [--cwd PATH] [--label TEXT] [--env KEY=VALUE] [--focus|--no-focus]
herdr pane list [--workspace ID] | current [--pane ID|--current] | get <pane_id>
herdr pane layout [--pane ID|--current] | process-info [--pane ID|--current]
herdr pane split [<pane_id>|--pane ID|--current] --direction right|down [--cwd PATH] [--no-focus]
herdr pane run <pane_id> <command>                    # atomically sends text + Enter
herdr pane wait-output <pane_id> (--match TEXT | --regex PATTERN) [--timeout MS] [--source ...]
herdr pane read <pane_id> [--source visible|recent|recent-unwrapped] [--lines N]
herdr pane close <pane_id>
```

`workspace list` includes a `worktree` object (`checkout_path`, `is_linked_worktree`, `repo_name`,
`repo_root`, `repo_key`) for workspaces opened on a worktree — the fastest way to map a live
workspace to a branch checkout. `pane split` returns the new pane as `.result.pane.pane_id`.
`pane wait-output` searches the selected snapshot immediately, so existing output can match.

Geometry rule: split `right` when the pane is wider than tall, `down` otherwise; avoid repeated
same-direction splits that produce unusable slivers; keep the user's focus with `--no-focus` and
preserve the caller's cwd explicitly with `--cwd "$PWD"`.

## API inspection

```
herdr api snapshot        # full live runtime state (workspaces, panes, agents) — ideal for recovery
herdr api schema --json   # exact request/response JSON shapes for every method
```

`snapshot` is read-only and is the cheapest ground truth for the recovery step. `schema` is the
right place to settle any question about a response field shape instead of guessing.

## CLI safety rules

- `--no-focus` for background work unless the user asked to switch context.
- Target `--current`, an explicit ID or a unique agent name; never rely on another client's focus.
- Do not close workspaces/tabs/panes/sessions you did not create unless the user explicitly asks.
  `workspace close --group` also closes linked worktree workspaces — never add it merely to bypass a
  `workspace_group_close_required` error.
- Never run `herdr server stop` unless the user explicitly intends to stop the server and its pane
  processes, and never kill the main Herdr process. Use a named test session for experiments that
  need an isolated server.
- After an update, client and server versions can differ: check `herdr status` before relying on new
  server features. A missing method is not permission to stop or upgrade a server.
- `herdr machine list` is a list of saved connection profiles, not a pane inventory; only add,
  remove, enable or disable profiles when the user asks.
