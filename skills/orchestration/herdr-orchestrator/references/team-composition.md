# Team composition and selection

`team_mode` decides **who chooses the team** - how many agents exist, which roles, which agent kinds,
whether an existing agent is reused, and the topology. It is independent of `coordination_mode` (who
approves) and of `worker_execution_mode` (how a worker is launched).

```yaml
team_mode: manual | semi_auto | auto        # default: semi_auto
team_constraints:                            # persisted, always honoured
  allowed_agent_kinds: []                    # e.g. [opencode]
  pinned_roles: {}                           # role or task id -> agent kind, e.g. {worker: opencode}
  max_workers: null
  notes: []
```

## The three modes

### `manual`

The user specifies agents/roles/kinds:

```text
coordination: auto      team: manual
  frontend -> opencode
  backend  -> opencode
  reviewer -> opencode
```

You decide **how** to coordinate (worktrees, DAG, dispatch order, monitoring, integration), but you do
not substitute the composition the user chose. Reusing an idle agent of the pinned kind is fine;
swapping the kind is not.

### `semi_auto`

The user fixes part of the team and you decide the rest:

```text
implementation must be opencode   (constraint)
reviewer: your call
number of implementation workers: your call
```

Honour every fixed part exactly, then resolve the rest as in `auto`.

### `auto`

You decide the number of agents, the roles, reuse vs creation, the agent kinds (when not constrained),
whether a researcher/tester/reviewer is needed, and the topology, based on the task and the resources
actually available on the host.

## Resolution procedure (bootstrap, every run)

1. Parse the user's current message for composition statements: "use only X", "X for the reviewer",
   "you decide the reviewer", "two workers at most". These become `team_constraints`; they are
   **composition** constraints, never coordination-mode changes.
2. Merge with the persisted `team_constraints` of the run (explicit instruction wins over persisted).
3. Inspect the live host: `herdr agent list` (live agents, kinds, cwd, state) and the kinds accepted by
   `herdr agent start --kind` on this machine. A kind is usable only if its CLI is installed.
4. Validate every pinned/required kind against that list**before** creating worktrees or agents.
   - If a pinned kind is unavailable, stop and ask (all modes): substituting a user-chosen kind is a
     material scope change.
   - With `team_mode: manual`, also stop if the requested roles cannot be staffed as specified.
5. Record the resulting composition in `tasks.json` (agent, kind) and the constraints in `state.json`.

## Selection heuristics (used only for what the mode leaves to you)

- Prefer a different kind (or at least a genuinely separate instance) for the reviewer, so the review
  is independent of the implementer; when only one kind is installed, use a separate instance, a
  separate pane, a separate cwd and a read-only prompt.
- Match capability to the work: implementation, migration and test-writing need a kind that can edit
  files and run commands; research and verification tasks can use read-only instances.
- Prefer reusing a live, idle agent of the right kind and cwd over creating a new one; never reuse an
  agent whose cwd or branch does not match the task.
- Keep the team as small as the DAG allows. "Agents are available" is not a reason to spawn more.

## Explicit boundary: no cost/model scoring yet

There is deliberately **no** scoring, cost-ranking or model-latency optimisation of agent kinds in
this version. That is a separate, future upgrade. Until then:

- every agent kind supported by the installed Herdr remains usable (`--kind <kind>`);
- explicit user choices always win over any preference of yours;
- when the mode leaves the choice to you, pick from the installed kinds and record the one-line reason
  in `decisions.md` (e.g. "reviewer: second opencode instance in a separate worktree; only one coding
  CLI installed on this host").

## Recording

```bash
python3 scripts/orch.py init   --team-mode semi_auto --allowed-agent-kind opencode --pin worker=opencode
python3 scripts/orch.py set-modes --team-mode manual --allowed-agent-kind opencode --max-workers 3 --note "user pinned the team"
```

`set-modes` logs a `mode_changed` event and a `decisions.md` line. Constraints recorded there survive
recovery and are re-applied on resume.
