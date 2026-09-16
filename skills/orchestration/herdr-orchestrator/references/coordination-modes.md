# Coordination modes

`coordination_mode` decides **who approves coordination checkpoints**. It says nothing about who is
on the team (`team_mode`) or how a worker CLI is launched (`worker_execution_mode`); the three axes
are independent and must never be inferred from one another.

```yaml
coordination_mode: assisted | supervised_auto | auto    # default: supervised_auto
```

## The three modes

### `assisted`

You plan, decompose, isolate and prepare, but ask the user before every relevant action:

```text
team creation      -> ask before starting any agent
run start          -> ask before dispatching the first mutating task
integration        -> ask before merging each accepted branch
cleanup            -> ask before removing any owned resource
```

Read-only work never needs approval: inspecting the runtime, reading Git, listing worktrees,
running read-only commands, writing state files, resolving task statuses from observation.

Shape: plan first, present the plan (tasks, criteria, scope, team, worktrees), then execute exactly
the approved plan; each later checkpoint is a separate, short request.

### `supervised_auto`

The default. You run the entire normal workflow autonomously - planning, DAG, worker creation,
worktrees, delegation, parallelism, monitoring, tests, review, fix loops, integration, validation,
cleanup - without asking for routine coordination decisions. You keep the user informed at meaningful
checkpoints (team ready, tasks dispatched, phase transitions, integration done, cleanup done,
completion) instead of asking permission.

You still stop and escalate for the triggers listed below.

### `auto`

You run the whole workflow with the minimum of interruptions and intermediate messages: plan,
decompose, build the DAG, create or reuse workers, delegate, honour dependencies, parallelise,
monitor, react to failures, run fix loops, test, review, integrate, validate, clean up and persist
state without routine confirmations. Report at phase boundaries and at the end rather than per step.

`auto` is **not** permission to ignore safety or ownership: see "Non-negotiables" below.

## Summary

| | `assisted` | `supervised_auto` | `auto` |
|---|---|---|---|
| plan | presented for approval | executed | executed |
| team creation | approval | autonomous + notice | autonomous, silent |
| dispatch | approval | autonomous | autonomous |
| integrate | approval per branch | autonomous + notice | autonomous |
| cleanup | approval | autonomous + notice | autonomous |
| progress updates | per checkpoint request | at checkpoints | phase boundaries + final |
| escalation triggers | always | always | always |

## Escalation triggers (all modes, including `auto`)

Stop and ask the user when:

- a security/trust decision is new and not already authorized (trusting a repository, a hook, a
  credential store, a destructive command, privilege escalation);
- credentials or authentication are required;
- the requested scope changes materially (new files/areas/components, a pinned agent kind is
  unavailable, the plan no longer fits the request);
- recovery state is ambiguous enough that continuing could duplicate work or destroy something;
- the requested work is clearly outside what the user authorized;
- continuing could affect resources or data outside the run (other repositories, other panes and
  workspaces, production systems, publishing, deploys, pushes).

Stopping means: record the situation in `decisions.md`, state the exact decision needed, and wait.
Never resolve one of these by choosing the permissive branch.

## Non-negotiables

No coordination mode, and no combination with `team_mode: auto` and
`worker_execution_mode: autonomous`, may weaken:

- the ownership ledger (touch only resources this run created);
- one worktree per mutating task;
- independent review before integration;
- the stop-on-conflict rule;
- never auto-answering a trust, hook, credential, sudo or ownership prompt;
- the escalation triggers above.

## Recording and changing the mode

- Resolve at bootstrap: the user's current explicit instruction wins, then the persisted run
  configuration, then the skill default.
- Persist with `python3 scripts/orch.py init --coordination-mode <mode>` or change later with
  `python3 scripts/orch.py set-modes --coordination-mode <mode> --note "<why>"`. The command appends a
  `mode_changed` event to `events.jsonl` and a timestamped line to `decisions.md`.
- A mode change during a run is a decision: say so in the next update, and never downgrade `assisted`
  to a more autonomous mode without an explicit instruction from the user.
- `assisted` may be left mid-run only by the user's instruction; on resume the mode is read back from
  the state file, so an interrupted `assisted` run resumes asking for approvals.
