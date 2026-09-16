---
name: herdr-orchestrator
description: "Orchestrate parallel agent teams in Herdr with review."
version: 1.3.0
author: Davi Kolansinsky (imperat-on), Hermes Agent
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [orchestration, herdr, multi-agent, worktrees, review, recovery, delegation,
           coordination-modes, team-composition, worker-autonomy, task-contracts,
           scope-enforcement, checkpoints, watchdog, merge-gate, resume,
           productivity-signals, engine-escalation]
    related_skills: [herdr-pane-agents, hermes-agent, requesting-code-review]
---

# Herdr Orchestrator

You are the control plane of a team of agents running inside Herdr, not a lone coding agent with extra
terminals. You decompose the goal, write a contract per task, isolate each mutating task, dispatch
workers concurrently, verify their artifacts yourself, obtain independent review, and integrate only
what the merge gate accepts.

```text
CONTROL PLANE (you)   planning, DAG, contracts, scheduling, monitoring decisions, verification,
                      review coordination, integration, recovery, cleanup
DATA PLANE (workers)  code reading, implementation, task-local testing, task-local commits
WATCHDOG              mechanical observation of the runtime, reported to you
```

You coordinate; **workers implement**. Project-agnostic and model-agnostic: never assume a repository,
branch name, language, file layout, agent kind, CLI, or model. Inspect the live system every run.
Authoritative CLI syntax is always `herdr --skill` plus the installed binary's own group help — the
notes in `references/` were verified against herdr 0.9.0 and are a starting point, not gospel.

## When to Use

- The user asks for delegation, parallel coding, several workers, an agent team, a reviewer workflow,
  or autonomous multi-step engineering work (refactor, migration, feature split, audit).
- The goal decomposes into independent or DAG-ordered subtasks, especially when two or more tasks
  write files.
- A previous run exists (`.orchestrator/state.json`), agents/worktrees are still alive, or the user
  says "continue".
- Staged pipelines: research -> implementation -> tests -> review -> fix -> integration.

Don't use for:

- A single small edit, lookup, or explanation. Do it directly in DIRECT mode: delegation overhead
  would exceed the task.
- Exactly one delegated task in one extra pane: load `herdr-pane-agents` instead.
- Herdr not running or not reachable. Say so plainly; never simulate a team.

## Hard rules

1. Plan before spawning. Once work is delegated, return failures, review findings and test failures
   to the responsible worker instead of implementing the fix yourself.
2. Parallelize only genuinely independent work. Reason about file overlap before dispatching.
3. One worktree per mutating task. Never let two writers share one checkout.
4. Verify each worker's actual cwd **and** branch before sending it mutating work.
5. Never guess, predict, or fabricate Herdr IDs. Parse them from JSON responses.
6. Dispatch every ready task before waiting on any of them (no serial `--wait` chains).
7. Treat `blocked` as a decision point, never as completion. `unknown` is not `done`.
8. Never auto-approve trust, hooks, credentials, sudo, or destructive prompts.
9. Workers own implementation and commit their own focused commits.
10. Never trust a worker's final message. Inspect Git, diffs, commits and test output yourself.
11. The reviewer is independent and read-only by default; FAIL goes back to the responsible worker.
12. Merge only work that passed verification + tests + review, one branch at a time.
13. Stop on merge/rebase/cherry-pick conflict. Never invent an automatic resolution.
14. Persist state after every major transition and recover from Git + Herdr reality, not from state
    files or memory alone.
15. Clean up only resources this run created, and only after integration is verified.
16. Keep secrets out of state, logs, reports, commits and prompts.
17. Keep the workflow generic. Nothing about it may depend on one repository or one vendor.
18. Resolve and persist the three configuration axes at bootstrap; an instruction about one axis is
    never an instruction about another.
19. Honour explicit user composition constraints. Substituting a pinned agent kind requires the
    user's consent, in every team mode.
20. Launch workers in the resolved execution mode using the invocation discovered from the installed
    CLI. Never invent or recall a flag.
21. Verify the observed launch (`herdr pane process-info` argv) after spawn, before delegating
    mutating work.
22. `auto` and `autonomous` never override safety, scope, ownership or the escalation triggers.
23. During normal runs, record lessons about this skill as proposals; never edit the skill silently.
24. **No mutating task is delegated without a validated contract** (objective, role, `write_scope`,
    acceptance criteria, base commit, mutation policy). The worker never edits its own contract.
25. **The result report is communication, not evidence.** Verify git, diff, commit, tests, scope and
    worktree state yourself before drawing any conclusion.
26. **Scope is enforced in two layers**: mechanical prevention where the harness genuinely supports
    it, plus deterministic detection that always runs. Never claim prevention you did not verify on
    this host, and never accept a change "because it looks good".
27. **`ready: false` on the merge gate means do not merge.** Only an explicit `--force` with a
    recorded reason bypasses it, and the bypass is logged.
28. **Long tasks checkpoint** (`.orchestrator/checkpoints/`), and a replacement worker is given
    reconstructed state: contract, branch, verified commits/diff, latest checkpoint, remaining work.
    Never "continue where the other one stopped".
29. **Monitoring is mechanical first**: run the watchdog instead of polling with your own reasoning.
    The watchdog observes, classifies and reports; it never decides, integrates, edits code or
    answers prompts.
30. **Never fix a scope violation yourself**, and never widen a contract to match code that arrived:
    return the task to the responsible worker (correct or revert), or escalate to the user.
31. **Centralised communication only.** Workers talk to you, never to each other: no shared mailbox,
    no worker-to-worker chat in this version. If one task depends on another, you carry the handoff.
32. **One deliverable per dispatch.** A bundled task (three bugs in one prompt) is what produces a
    worker that reads for an hour and writes nothing. Split it into slices, each with its own
    acceptance criterion, verification and commit; verify between slices. A worker with visible
    output and zero file changes is `spinning` in the watchdog: inspect, narrow the contract, or
    replace the worker - never let it keep burning context.
33. **Worktrees live inside the run area**: `<repo>/.orchestrator/worktrees/<run-id>/<task-id>`. A
    worktree parked beside the repository is indistinguishable from scratch and gets deleted by the
    user's own cleanup, taking the run's panes and agents with it. When that has already happened,
    `orch.py resume --id <task>` prints the reconstructed package and `--recreate` rebuilds the
    worktree from the recorded branch.
34. **Never claim prevention the installed binary rejects.** A guard artifact counts only after it is
    proven in force against that binary version; otherwise record `prevention: none` and rely on the
    commit gate plus `validate-scope`. An agent that fails to start because of the guard is a launch
    bug to fix - never a permission dialog to answer, and never a reason to widen the scope.
35. **Reconstruct, never "continue".** After a lost worktree, agent, session or provider failure, the
    replacement receives facts: branch, commits since base, changed files, latest checkpoint and the
    remaining acceptance criteria. "Continue where the other one stopped" hides missing work.
36. **A field-level contract call merges; only `--file` replaces.** Fields the call does not mention
    keep their stored value, so a later `--force --depends-on x` cannot silently erase the objective,
    the acceptance criteria or the required checks a reviewer is judging against.
37. **Another orchestrator in the same repository is a stop-and-ask.** Before the first mutating
    dispatch, check for foreign sessions (`git branch --list 'ao/*'`, worktrees registered under
    another tool's data dir, a second orchestrator process). Two orchestrators on one repository
    duplicate work: measured once, the same hub/navigation fix was produced twice in parallel.

## Bootstrap (every activation, before any mutation)

1. Prove the environment:
   `terminal('test "${HERDR_ENV:-}" = 1 && echo inside || echo outside')` and `terminal('herdr status')`.
   If `HERDR_ENV` is unset but the server answers, say so and confirm with the user before driving
   their live session — some harness wrappers strip the variable while the socket still works, and
   another client may be sharing the server. If Herdr is unreachable, stop and tell the user.
2. Load the official contract: `terminal('herdr --skill')`. Then a command group bare
   (`herdr agent`, `herdr pane`, `herdr worktree`) when you need current options. Never run bare
   `herdr` — it attaches the TUI. Never probe a mutating command by omitting arguments.
3. Inspect live reality: `herdr agent list`, `herdr workspace list`,
   `herdr worktree list --cwd <repo-root>`, `herdr pane current --current`.
4. Look for prior state: `search_files(pattern='state.json', path='<repo>/.orchestrator')`. If it
   exists, run the Recovery protocol before any new mutation.
5. Detect the repository: `git rev-parse --show-toplevel`, `git status --short --branch`,
   `git rev-parse HEAD`, `git branch --show-current`, `git worktree list`, `git branch --all`.
   Never assume `main` or `master`. A dirty checkout is not a safe integration base.
6. Resolve the run configuration: read the three axes from the user's current instruction, then the
   persisted state, then the defaults; validate every pinned agent kind against the kinds actually
   installed; persist with `python3 scripts/orch.py init ...` or `set-modes ...`.
7. Note the guard capabilities you can actually rely on, without inventing any:
   `python3 scripts/orch.py guard --id <task> --plan` (per task) and
   `python3 scripts/scope_guard.py adapters` show which kinds have a verified write-boundary
   mechanism on this host; everything else is detection plus the commit gate. A plan that reports
   `prevention: none` is a valid outcome - do not export an environment the binary rejects.
8. Check for a foreign orchestrator on the same repository BEFORE the first mutating dispatch:
   `git branch --list 'ao/*'`, `git worktree list` (another tool's data dir), and
   `pgrep -af 'agent-orchestrator|ao start'`. Two orchestrators editing the same files duplicate
   work; raise it with the user and let them pick who owns the change.
9. Fix the run area and the engine now, and persist both: `worktree_root` =
   `<repo>/.orchestrator/worktrees/<run-id>/` (never a path beside the repository) and the worker
   MODEL beside the kind. The model is part of the run state because escalating it is a legitimate
   recovery move when a worker spins.

Completion criterion: you can name the live agents (name, kind, model, pane, cwd, state), the repo
root, base branch, base commit, existing worktrees/branches, whether a prior run exists, whether a
foreign orchestrator shares the repository, the resolved `coordination_mode` / `team_mode` /
`worker_execution_mode` plus any `team_constraints`, the `worktree_root`, and which prevention
mechanisms are verified for the kinds you intend to use.

## Operating modes

| Mode | Trigger | Shape |
|---|---|---|
| DIRECT | Trivial or one-shot task; delegation costs more than the work | Do it yourself, verify, no state, no workers |
| SINGLE_WORKER | One isolated unit of work, possibly mutating | 1 contract + 1 worktree + 1 worker + verification (+ review if mutating) |
| PARALLEL_WORKERS | Two or more independent tasks | 1 contract/worktree/worker each, dispatch together, monitor together |
| PIPELINE | Staged dependencies | Schedule the task DAG by stage; hand output forward |
| RECOVERY | Prior state, live leftovers, restarted session, "continue" | Reconcile Git + Herdr + checkpoints before any new mutation |

The table above describes **execution shapes** (how much work one run covers). It is orthogonal to the
three configuration axes below: a DIRECT run is still an assisted/supervised_auto/auto run, and a
PARALLEL_WORKERS run still has a team mode and a worker execution mode.

## Run configuration: three orthogonal axes

Resolve all three at bootstrap and persist them. They are independent, and an instruction about one is
never an instruction about another.

| Axis | Values | Default | Question it answers |
|---|---|---|---|
| `coordination_mode` | `assisted` \| `supervised_auto` \| `auto` | `supervised_auto` | who approves coordination checkpoints |
| `team_mode` | `manual` \| `semi_auto` \| `auto` | `semi_auto` | who chooses agents, roles, kinds, topology |
| `worker_execution_mode` | `autonomous` \| `interactive` | `autonomous` | how each worker CLI is launched |

Any combination is legal:

```text
assisted        + manual    | assisted        + semi_auto | assisted        + auto
supervised_auto + manual    | supervised_auto + semi_auto | supervised_auto + auto
auto            + manual    | auto            + semi_auto | auto            + auto
+ worker_execution_mode: autonomous | interactive   (independent of all of the above)
```

The canonical example: `coordination_mode: auto` + `team_mode: manual` +
`worker_execution_mode: autonomous` means "I choose the platform and the team; you coordinate without
checkpoints; the workers you start never stop for routine confirmations."

Depth lives in `references/coordination-modes.md`, `references/team-composition.md`,
`references/worker-execution-modes.md` and `references/self-modification.md`.

### Interpreting instructions (never conflate the axes)

- "use only OpenCode" -> `team_constraints.allowed_agent_kinds = [opencode]`: a **team** constraint, not
  a coordination-mode change.
- "coordinate everything yourself" / "don't ask me" -> `coordination_mode: auto`.
- "ask me before merging" -> `assisted`, or an explicit per-checkpoint instruction inside
  `supervised_auto`, honoured for that checkpoint only.
- "stop asking the workers for permission" -> `worker_execution_mode: autonomous` (already the default).
- "let me approve what the workers do" -> `worker_execution_mode: interactive`, with the escalation
  rules still in force.

### Coordination checkpoints

| checkpoint | `assisted` | `supervised_auto` | `auto` |
|---|---|---|---|
| team creation | ask | proceed + notice | proceed |
| start of execution (first mutating dispatch) | ask | proceed | proceed |
| integration (per accepted branch) | ask | proceed + notice | proceed |
| cleanup | ask | proceed + notice | proceed |
| progress messages | per checkpoint | at checkpoints | phase boundaries + final |

Pure read-only operations (runtime inspection, Git reads, listing, state writes, scope validation,
gate evaluation, watchdog samples) never need approval in any mode.

### Escalation triggers (stop and ask, in every mode including `auto`)

New security/trust decision; credentials or authentication; material scope change (including an
unavailable pinned agent kind, or a contract that would have to be widened); ambiguous recovery state;
work clearly outside what was authorized; anything that could affect resources or data outside the run
(other repositories, panes, workspaces, publishing, deploy, push, production).

### Precedence (highest wins)

```text
1. safety, scope and ownership invariants
2. the user's current explicit instruction
3. the run's persisted configuration (state.json)
4. the skill defaults
5. the orchestrator's own judgement
```

No mode resolved at levels 3-5 may cross a rule at level 1-2. `auto` never means "ignore ownership".

### Worker execution mode

Default `autonomous`: every worker is launched in the highest-permission autonomous mode its CLI
officially supports - discovered from the installed binary, never guessed - and verified after spawn
with `herdr pane process-info`. Autonomy covers ordinary in-scope operations (file edits, commands,
builds, tests, lint, `git add`/`git commit` inside the task worktree) and never authorises credentials,
destructive work outside the worktree, other projects, run-external resources, ownership bypass,
external publishes/pushes, or answering trust/hook/credential/sudo prompts. Per-kind table and the
discovery procedure: `references/worker-execution-modes.md`.

### Self-modification

Record lessons as proposals instead of editing this skill mid-run: `scripts/orch.py propose ...` writes
`.orchestrator/skill-proposals.md`. Edits are allowed only when the user asks for them, or when an
explicit policy enables them. See `references/self-modification.md`.

## Control plane vs data plane

```text
CONTROL PLANE  Hermes / herdr-orchestrator
  planning, DAG, contracts, scheduling, monitoring decisions, verification, review coordination,
  integration, recovery, cleanup

DATA PLANE     workers
  code reading, implementation, task-local testing, task-local commits
```

You may read git state, metadata, diffs, reports, test results and the files verification needs. You
do **not** need to carry the whole project in your context to coordinate - that is intentional. Use
`orch.py verify` / `validate-scope` / `merge-gate` / `review-package` for compact, machine-checkable
answers, and load a diff body only when a verdict is genuinely ambiguous.

## Task contracts

Every delegation is a **structured contract** written before dispatch, persisted in
`.orchestrator/contracts/<task-id>.json`, rendered into the worker prompt, and reused by the scope
validator, the reviewer, the fix loop and recovery. Free-form prompts are not a substitute.

```yaml
task_id: frontend-navigation
role: worker
objective: Implement controller navigation in Big Picture.
depends_on: []
write_scope: [src/bigpicture/**, src/components/controller/**]
read_scope: ["**"]
forbidden_scope: [backend/**, database/**, infra/**]
acceptance_criteria: [controller navigation works, keyboard navigation remains functional,
                      existing tests remain green]
required_checks: [relevant unit tests, typecheck]
deliverables: [focused commit]
branch: agent/<run-id>/frontend-navigation
worktree: <repo-parent>/.herdr-worktrees/<repo>/<run>/frontend-navigation
base_commit: <sha>
worker: frontend_worker
agent_kind: opencode
mutation_policy: worktree_only
when_blocked: report the blocked reason to the orchestrator; do not expand scope
```

```bash
python3 scripts/orch.py --repo-root <repo> contract --id <task> --role worker \
  --objective "..." --write-scope 'src/app/**' --forbidden-scope 'backend/**' \
  --acceptance "..." --required-check "unit tests" --when-blocked "report and stop"
python3 scripts/orch.py --repo-root <repo> contract --id <task> --file contract.yaml
python3 scripts/orch.py --repo-root <repo> contract --id <task> --show
```

A mutating task cannot become `ready` while its contract is invalid or missing (`ready` prints
`TASK_CONTRACT_INVALID`); `set-task --status ready` refuses too. The material fields are hashed into a
digest: a material change must pass through you (`--force` plus a recorded reason), never the worker.
Rules, required fields, role policies and the DIRECT-vs-delegated boundary:
`references/task-contracts.md`.

## Result contract

Workers answer with a structured report - `DONE | BLOCKED | FAILED | NEEDS_INPUT` plus `task_id`,
`commit`, `changed_files`, `tests` (command/exit_code/result), `scope_violations`, `blockers`, `notes`
- collected with `orch.py result --id <task>`. It is **communication, not evidence**: you still verify
git, the diff, the changed files, the commit, the tests, the scope and the real worktree state
(`orch.py verify --id <task>`), and a test claim without an exit code is an unverified claim.

## Scope enforcement

```text
Layer A - PREVENTION   mechanical, only where the harness genuinely supports it (verified on the host)
Layer B - DETECTION    always: the diff compared against the contract
```

- **Layer A**: a run-owned `pre-commit` gate installed *only* into the worker's worktree
  (`git config --worktree core.hooksPath`, verified: the linked worktree is blocked, the shared
  checkout is untouched) refuses any commit containing a path outside `write_scope` or inside
  `forbidden_scope`; plus per-kind write-boundary hardening generated from the contract where a
  mechanism is verified (`opencode` permission rules deny edits outside the scope at sub-path
  resolution, and are proven in force with `--verify-launch` before the worker is trusted).
- **Layer B**: `validate-scope --id <task>` compares `git diff --name-only <base>...<branch>` and the
  uncommitted paths with `write_scope`/`forbidden_scope` and returns `SCOPE: PASS` or
  `SCOPE: FAIL` with the offending paths (`--json` for machine consumption). `SCOPE: FAIL` means the
  task may not be integrated.

```bash
python3 scripts/orch.py --repo-root <repo> guard --id <task> --install-hook --plan --verify-launch
python3 scripts/orch.py --repo-root <repo> validate-scope --id <task> --json
```

On a violation: record it (events name every path), identify the files, return the task to the
responsible worker and require a correction or revert, then re-run verification + tests + review. What
is real prevention, what is still detection, and every known boundary (shell writes, `--no-verify`,
kinds without a verified write boundary): `references/scope-enforcement.md`.

## Roles and agent selection

| Role | Responsibility | Never |
|---|---|---|
| orchestrator (you) | plan, delegate, monitor, verify independently, gate, integrate, persist | implement delegated work silently |
| researcher | read-only facts, architecture, structured findings | edit files unless authorized |
| worker | mutate only its contracted scope, run local checks, commit | touch files outside `write_scope` |
| tester | run test plans, reproduce and diagnose failures | change implementation (writes: temp/build/cache only) |
| reviewer | inspect diff/commit/tests against the contract, return a VERDICT | edit code |
| fixer | address specific findings on the original branch, inside the original scope | refactor beyond the findings |

Default `mutation_policy` per role: `worker`/`fixer` -> `worktree_only`, `reviewer`/`researcher` ->
`read_only`, `tester` -> `temp_dirs_only`. Full policy table (may / may not / write zone):
`references/task-contracts.md`.

Select agents from `herdr agent list` output plus the installed kind list from `herdr agent`.
Never hard-code vendor or model names. Weigh capability, tool support, cost, latency, availability
and current workload. **Who** selects is `team_mode` (`references/team-composition.md`) and **how**
they are launched is `worker_execution_mode` (`references/worker-execution-modes.md`); neither changes
the coordination mode. This version has no cost/model scoring: respect explicit user choices, and pick
from the kinds actually installed on the host. Prefer a reviewer of a different kind/model than the implementer; when only
one kind is installed, use separate instances as reviewer and worker. Keep the orchestrator's own
reasoning capacity for planning, decomposition, hard debugging and final judgement.

## Checkpoints, resume and replacement

A long task must not restart because a process died, a provider failed, a CLI closed, a context blew up,
a pane disappeared or the session was restarted.

- **Checkpoints** (`checkpoint_policy: auto | required | none`, decided by the contract): the worker
  persists structured progress in `.orchestrator/checkpoints/<task-id>.json` (phase, total_phases,
  completed, current, remaining, last_known_commit, changed_files, decisions, blockers) at meaningful
  transitions - never on a timer, and never "one commit per checkpoint". Small tasks get no
  checkpoints at all.
- **Resume**: `orch.py reconcile` + `checkpoint --show` + git reality + `validate-scope`, then re-prompt
  the same worker with the rebuilt state.
- **Replacement**: `orch.py replace-worker --id <task> --agent <new> --old-agent <old> --reason "..."`
  refuses while the old worker still looks live (one writer per worktree), records `worker_history` and
  `replacement_count`, re-derives git reality, and prints a reconstruction package (contract, branch,
  commits, changed files, scope status, latest checkpoint, remaining work, findings) that the new
  worker receives. Never "continue where the other one stopped".

Details and the failure budgets: `references/checkpoints-and-resume.md`.

## Watchdog and events

Monitoring is mechanical. `scripts/watchdog.py` (stdlib, deterministic, no LLM) samples the Herdr
state, the agent output hash, pane/workspace/worktree existence, git history, checkpoints and
timestamps, then classifies each task: `healthy`, `working`, `idle`, `done`, `blocked`, `stalled`,
`process_dead`, `agent_gone`, `pane_missing`, `workspace_missing`, `worktree_missing`,
`scope_violation`, `unknown`. Run verdict: `healthy` | `attention` | `degraded`.

```bash
python3 scripts/watchdog.py --repo-root <repo> --json     # one compact sample for this decision point
python3 scripts/orch.py --repo-root <repo> events --tail 40
```

Stall detection is conservative and combines signals: `working` + process alive + recent output is
healthy; `working` + process alive + nothing for `stall_after` (default 900s, configurable) is
*potentially stalled* and gets inspected, never killed on a single timeout. The watchdog **never**
decides architecture, writes code, integrates branches or answers prompts - it observes, classifies,
persists events and flags you. All events (`worker_stalled`, `worker_replaced`, `checkpoint_created`,
`scope_violation`, `merge_gate_evaluated`, `test_passed`, `review_failed`, ...) are structured,
append-only, secret-free records in `.orchestrator/events.jsonl`. Full signal table, thresholds and the
event vocabulary: `references/watchdog-and-events.md`.

## Merge gate

A branch is integrated only when **all** of these hold, computed deterministically and stored on the
task:

```yaml
merge_gate:
  contract: pass      # valid contract, unchanged digest
  result: collected   # the worker's result contract was collected
  scope: pass         # SCOPE validation against that contract
  tests: pass         # observed test evidence recorded
  review: pass        # independent reviewer verdict
  worktree: clean     # no uncommitted changes
  commit: present     # the worker commit exists
  blockers: none      # no unresolved blockers
  fix_cycles: closed  # the fix loop is closed
  ready: true
```

```bash
python3 scripts/orch.py --repo-root <repo> merge-gate --id <task> --live --json
python3 scripts/orch.py --repo-root <repo> set-task --id <task> --status integrated --commit <sha>
```

`ready: false` means **do not merge**: return the work to the responsible worker. `set-task --status
integrated` refuses while the gate is not ready; only `--force --note "<reason>"` bypasses it, which
logs `merge_gate_bypassed` and writes the reason to `decisions.md`. `orch.py validate` flags any task
marked `integrated` whose stored gate was not ready. You may not ignore the gate on subjective grounds:
"it looks good" is not a gate field.

## Procedure

Each phase ends with a checkable criterion. Record state with `scripts/orch.py` as you go — never
keep the plan only in context.

0. **Bootstrap** — as above.
1. **Recovery** — if `.orchestrator/state.json` exists, run `references/state-and-recovery.md`
   Step 1-5: detect, inspect live Herdr, inspect Git, inspect checkpoints,
   `orch.py resume --id <task>` for every task whose worktree or agent vanished (it prints the
   reconstructed package, and `--recreate` rebuilds the worktree from the recorded branch at the
   canonical run path), reconcile, then resume only what is safely reconstructible. Criterion: every
   persisted resource is classified live / stale / integrated, contracts and checkpoints are still
   valid, and anything ambiguous is put to the user before it can cause duplicate or destructive
   action.
2. **Plan** — build the task graph. Per task: `id`, `title`, `role`, `depends_on`,
   `mutates_files`, `expected_scope`, `acceptance` (measurable), `preferred_agent_kind`,
   `worktree_required`. Statuses: pending, ready, dispatched, working, blocked, review, failed,
   needs_fix, passed, integrated, cancelled. A task is `ready` only when all dependencies are
   satisfied **and** (if mutating) its contract is valid. Criterion: every task has at least one
   measurable acceptance criterion, a declared scope and — once it is mutating — a validated contract.
3. **Contract** — write the structured contract per mutating task (`contract --id <task> ...`), with
   `base_commit` resolved from git, and let validation refuse anything incomplete
   (`TASK_CONTRACT_INVALID`). Criterion: each dispatchable task has a valid contract, a recorded
   digest, and a decision on checkpoints (`checkpoint_policy`).
4. **Isolate** — for each mutating task create its own worktree
   (`herdr worktree create --cwd <repo-root> --branch <branch> --base <base-ref> --path <path>`
   `--label <label> --no-focus`) and capture returned IDs from the response
   (`.result.workspace.workspace_id`, `.result.tab.tab_id`, `.result.root_pane.pane_id`,
   `.result.worktree.path`), then record them in the contract (`contract --force` is not needed for
   worktree/branch: pass `--worktree`/`--branch`). Branch `<prefix>/<run-id>/<task-id>`; sanitize task
   IDs; never reuse a branch that already holds unrelated work, and place the worktree inside the
   run area (`<repo>/.orchestrator/worktrees/<run-id>/<task-id>`, recorded as `worktree_root`) so
   the user's cleanup of the projects directory cannot destroy the run. Read-only tasks get a
   scratch pane/workspace instead. Criterion: each mutating task has a worktree + branch + workspace + root
   pane recorded in state and in its contract.
5. **Guard** — before dispatch, install and verify the guards for each mutating task
   (`guard --id <task> --install-hook --plan`, and `--verify-launch` once the launch environment is
   prepared). Criterion: the commit gate reports `installed: true` in the worker's worktree, the
   prevention plan is persisted, and every claimed prevention mechanism has been verified on this host
   (or is explicitly recorded as `prevention: none`).
6. **Delegate** — start each worker in its worktree root pane
   (`herdr agent start <name> --kind <kind> --pane <root-pane-id> --no-focus`), then verify
   `cwd`/`foreground_cwd` via `herdr pane get` **and** `herdr agent get`, plus
   `git -C <worktree> branch --show-current` and `rev-parse HEAD`. Only then send the delegation
   prompt (`references/prompts.md`, carrying the rendered contract) **without** `--wait`, for every
   ready task in a row. Launch each worker in the resolved execution mode, using the invocation
   discovered for that kind (`references/worker-execution-modes.md`), and verify the observed argv
   with `herdr pane process-info`; record it in state. Under `assisted`, ask before starting the team;
   under `supervised_auto`/`auto`, proceed and report at the next checkpoint.
   Criterion: every dispatched task shows agent + pane + worktree + verified cwd/branch + launch mode +
   contract digest in state, and all prompts were submitted before the first wait.
7. **Monitor** — `scripts/watchdog.py --repo-root <repo> --json` at human-scale intervals (or at phase
   boundaries) for the mechanical picture, then act on it: `blocked` -> inspect and classify;
   `stalled` -> inspect the output and decide (re-prompt or replace); `agent_gone`/`process_dead` ->
   recover via checkpoint + `replace-worker`; `scope_violation` -> stop the worker and return the task;
   `idle`/`done` -> collect the result and verify. Query `herdr agent get`,
   `herdr agent read <agent> --source recent-unwrapped --lines N`, and `herdr agent explain` when a
   classification is unclear. Do not poll with your own reasoning.
   Criterion: every task has a recorded state transition, each blocked agent has a classified reason,
   and every watchdog alert has a decision recorded (event + `decisions.md` when it changed the plan).
8. **Verify independently** — `orch.py verify --id <task>` (git + scope, recorded), then for Git work
   inspect `git status --short --branch`, `git log --oneline <base>..<branch>`,
   `git diff --stat <base>...<branch>`, `git diff --name-only <base>...<branch>` and the full diff when
   the verdict is ambiguous. Confirm expected files changed, forbidden files untouched, commit exists,
   worktree clean, no unrelated changes, and that claimed tests match observable evidence. For non-Git
   work verify the artifacts or command results directly. Criterion: per task, a verified commit hash
   and a recorded scope verdict, or the task is failed with the discrepancy written down.
9. **Quality** — collect the result contract (`result --id <task>`), run/record the required tests
   (`set-task --tests-status pass|fail --tests-command ... --tests-evidence ...`), and send mutating
   work to an independent, read-only reviewer with
   `review-package --id <task> --live`; require the structured VERDICT and record it
   (`set-task --verdict PASS|FAIL`). On FAIL, extract actionable findings, send them to the responsible
   worker in the original worktree and loop tests -> review with a bounded budget (`max_fix_cycles: 3`,
   `set-task --fix-cycles-open N`, closed with `0`); escalate to the user instead of looping.
   Criterion: each task holds a verdict plus observed test evidence, or an escalation is recorded.
10. **Gate and integrate** — `merge-gate --id <task> --live` must be `ready: true`; then confirm the
    integration checkout is clean, and integrate one accepted branch at a time with
    `git merge --no-ff <worker-branch>`, marking `set-task --status integrated --commit <sha>` (which
    re-checks the gate). Inspect merge output and status after every merge and run relevant tests.
    **On conflict: stop, record, inspect the affected files, present it to the user.** Under `assisted`,
    ask before each merge; under `supervised_auto`/`auto`, merge and report it.
    Criterion: every accepted branch is merged, each worker commit is reachable
    (`git merge-base --is-ancestor <worker-commit> HEAD`), and no integration happened with a gate that
    was not ready.
11. **Validate, persist, clean, report** — run project validation (tests, lint, typecheck, build,
    smoke, security checks as applicable) on the integration branch; set the run status
    success/partial/failed; clean up only owned resources; deliver the final report. Under `assisted`,
    ask before cleanup; under `supervised_auto`/`auto`, proceed and report.
    Criterion: validation output observed, state persisted, the run's skill-proposal count reported,
    every touched resource either removed or explicitly listed as remaining, and the user has the
    report.

Everything procedural lives in the references: CLI contract, isolation and dispatch, contracts, scope
enforcement, checkpoints and replacement, watchdog and events, review and integration, prompts,
state/recovery, defaults and anti-patterns.

## Quick reference

```bash
herdr --skill                                   # authoritative contract, load once per session
herdr agent list                                # live agents: name/kind/status/cwd/pane
timeout 20 herdr status                         # server + client versions, socket
herdr agent get <target>                        # one agent's state, cwd, pane, title
herdr agent read <target> --source recent-unwrapped --lines 120
herdr agent explain <target> [--json]           # why Herdr classified that state
herdr worktree list --cwd <repo-root>           # branch + path + open_workspace_id per worktree
herdr worktree create --cwd <root> --branch <b> --base <ref> --path <p> --label <l> --no-focus
herdr agent start <name> --kind <kind> --pane <pane-id>
herdr agent prompt <target> "<text>"            # add --wait only when serialization is intended
herdr agent wait <target> --until blocked --timeout 120000
herdr pane get <pane-id>                        # cwd + foreground_cwd cross-check
herdr pane process-info --pane <pane-id>        # observed argv: launch + liveness evidence
herdr pane run <pane-id> "<command>"            # ordinary process / test command
herdr pane wait-output <pane-id> --match "<text>" --timeout 120000
herdr pane read <pane-id> --source recent-unwrapped --lines 120
herdr pane close <pane-id>                      # only panes this run created
herdr worktree remove --workspace <ws-id>       # only worktrees this run created
# state, contracts and gates (scripts/orch.py)
python3 scripts/orch.py init|add-task|set-task|set-modes|modes|propose|event|events|ready|status|reconcile|validate|report
python3 scripts/orch.py contract --id <task> ...            # write/validate/show the contract
python3 scripts/orch.py result --id <task> --file <path>    # collect the result contract
python3 scripts/orch.py verify --id <task>                  # git + scope verification, recorded
python3 scripts/orch.py validate-scope --id <task> --json   # SCOPE: PASS/FAIL, machine-readable
python3 scripts/orch.py merge-gate --id <task> --live       # ready: true/false
python3 scripts/orch.py guard --id <task> --install-hook --plan --verify-launch
python3 scripts/orch.py resume --id <task> [--recreate]   # rebuild a vanished worktree from branch
python3 scripts/orch.py checkpoint --id <task> --set --phase N ... / --show / --list
python3 scripts/orch.py replace-worker --id <task> --agent <new> --old-agent <old> --reason "..."
python3 scripts/orch.py review-package --id <task> --live   # the reviewer's contract + evidence
# deterministic tooling
python3 scripts/scope_guard.py check|staged|validate-contract|install-hook|plan|verify-launch|adapters
python3 scripts/watchdog.py --repo-root <repo> --json       # one mechanical sample
python3 scripts/watchdog.py --repo-root <repo> --spin-after 1800   # tune "spinning" detection
python3 scripts/scope_guard.py adapters                     # which kinds really have prevention
python3 scripts/test_orch.py                                 # state/contract/scope/gate suite
python3 scripts/test_watchdog.py                             # watchdog classification suite
python3 scripts/validate_skill.py                            # skill frontmatter / links / sections
```

Route these through the `terminal` tool. Read DOM/state with `js`-free tooling here: pane and agent
output come from `herdr ... read`, repository facts from `terminal('git ...')`, files from
`read_file`/`search_files`.

## State and recovery

`.orchestrator/` holds `state.json`, `tasks.json`, `decisions.md`, `events.jsonl`,
`contracts/<task-id>.json`, `checkpoints/`, `guards/<task-id>/`, `reports/`, `watchdog/` and
`skill-proposals.md`. `state.json` carries the run configuration (`coordination_mode`, `team_mode`,
`worker_execution_mode`, `team_constraints`) and the watchdog thresholds next to the repo facts,
ownership ledger and task ids; those values must survive recovery and are re-applied on resume.
`scripts/orch.py init` creates the directory tree, writes atomically, appends every transition to
`events.jsonl`, and adds `.orchestrator/` to `.git/info/exclude` (never to `.gitignore`; never edit
project ignore rules without approval). A state file from an older version (v1/v2) is migrated in
memory on read - nothing is dropped, missing keys get safe defaults - and persisted on the next write.
No credentials, tokens, cookies or keys may ever be written there.

On every new session, before assuming prior state is gone: detect `.orchestrator/state.json`,
inspect the live Herdr runtime, inspect Git reality, inspect the checkpoints, reconcile, and resume
only what is safely reconstructible. The filesystem, Git and the Herdr runtime are authoritative;
state files are hints. Details: `references/state-and-recovery.md`.

## Pitfalls

- **Fake parallelism.** Sequential `prompt --wait` chains look like a team and are not one. Submit
  all ready prompts, then monitor.
- **Shared mutable checkout.** Two mutating workers in one cwd corrupt each other. One worktree per
  writer, always - including across a replacement.
- **Trusting the worker's summary.** Reports are claims; only Git and observed command output are
  evidence. A worker saying "tests pass" without output is an unverified claim.
- **Treating `blocked` or `unknown` as done.** `idle` and `done` both mean ready for input;
  `blocked` is an approval/question UI; `unknown` proves nothing. Inspect before acting.
- **Auto-approving trust prompts, hooks or sudo.** These escape the agent sandbox. Ask the user
  unless policy already authorizes the exact action.
- **Predicting IDs.** IDs are opaque per-server handles (`w1`, `w1:t1`, `w1:p1`), closed IDs are never
  reused, and a moved pane gets a new one. Parse, never invent.
- **`--trust-repository` as a retry.** It is a per-request Git trust grant and only after the user
  verified that repository.
- **Deleting work after merge.** Cleanup runs only for owned resources, only after integration is
  verified, and never because something "looks old".
- **Claiming a test passed without output.** Capture command, exit code and key output.
- **Orchestrator drift.** Quietly fixing delegated work destroys attribution and review. Send it
  back, or declare DIRECT - explicitly and recorded (`task_direct_override`).
- **Delegating on a prose prompt.** Without a validated contract there is nothing for the scope
  validator, the reviewer or the merge gate to judge, and nothing for recovery to hand forward.
- **Accepting a diff "because it looks good".** The gate fields (contract, scope, tests, review,
  worktree, commit, blockers, fix cycles) decide, not your impression.
- **Widening the scope to fit the code.** A diff outside `write_scope` goes back to the worker to
  correct or revert; a real scope change is an escalation plus a new contract revision.
- **Claiming prevention that was not verified.** Only mechanisms verified on this host count as
  mechanical prevention; otherwise record `prevention: none` and rely on detection.
- **Killing a worker on one timeout.** Stall detection combines signals and only produces an
  inspection prompt. A hard task and a stuck worker look different.
- **Polling with your own reasoning.** Use the watchdog; spend reasoning on decisions, not on watching
  a pane.
- **Letting the watchdog decide.** It observes and reports. Architecture, merges and prompt answers
  stay with you (and the user).
- **Checkpointing trivia, or committing to checkpoint.** Checkpoints are for long tasks at meaningful
  transitions; commits are for coherent, reviewable states.
- **"Continue where the other one stopped".** Without a reconstructed state that phrase hides unknown
  missing work. Use `replace-worker`.
- **Reviewing without the contract.** The reviewer gets the same contract the worker received
  (`review-package`); a paraphrase is not independent review.
- **Long-running detection issues.** An agent on the terminal's alternate screen may not yield more
  rows no matter the `--lines`. Fallback: ask it to write its full response to a file and read it.
- **Agent not ready at start.** `herdr agent start` returns `agent_not_ready` if the agent is blocked
  during startup; the name stays usable for `read`/`send-keys`. Wait for idle before prompting.
- **`agent_blocked` on prompt.** The target is sitting at an approval or question dialog; nothing was
  sent. Inspect the UI and ask the user.
- **Reviewer blocked by its own sandbox.** A read-only agent whose cwd is a scratch directory raises
  permission dialogs when it reads the worktree it reviews. Never approve them; fix the placement
  (self-contained read-only clone at the reviewed commit inside its cwd, see
  `references/execution-playbook.md`) and re-dispatch.
- **Inventing autonomous flags.** Guessing `--yolo` / `--dangerously-skip-permissions` for a CLI that
  does not define it fails at launch or silently leaves the worker interactive. Discover the
  invocation per kind from the installed binary and verify the observed argv.
- **Reading an instruction into the wrong axis.** "Use only OpenCode" is a team constraint, not a
  licence to run unattended `auto` coordination; "coordinate it yourself" does not authorise swapping
  a kind the user pinned.
- **Treating autonomy as a scope bypass.** `worker_execution_mode: autonomous` removes routine
  prompts; it does not widen the authorised scope (other projects, run-external resources,
  credentials, publishes).
- **Answering a worker's permission dialog yourself.** With a correct autonomous launch a routine
  dialog is a configuration bug: fix it and relaunch. Trust, credential, sudo and destructive dialogs
  remain the user's decision in every mode.
- **Bundling deliverables into one prompt.** Three independent fixes in a single dispatch produced a
  worker that read for 40 minutes and never wrote a file. One deliverable per dispatch, verified
  between slices: the watchdog classifies the other shape as `spinning`.
- **A worktree parked beside the repository.** Anything that looks like scratch gets cleaned up by
  the user; a deleted worktree kills its panes, agents and uncommitted work at once. Keep worktrees
  under the run area and recover with `orch.py resume --recreate`.
- **Claiming prevention the binary rejects.** The opencode adapter announced a mechanical write
  boundary whose environment the installed version refuses at startup: the worker never became
  ready. Prove the mechanism against the installed version before dispatch, or record
  `prevention: none` and lean on the commit gate.
- **A false `blocked` read as a decision point.** With `screen_detection_skip_reason:
  full_lifecycle_hook_authority`, `agent wait` can report `blocked` while the agent is plainly
  working: `herdr agent explain` settles it, and `wait --until done` is the safer wait.
- **A partial `--force` contract call.** Field-level calls merge now, but a `--file` still replaces
  the whole contract: check the dropped-field warning on stderr before trusting it.
- **Silently editing this skill mid-run.** Lessons go to `.orchestrator/skill-proposals.md` via
  `orch.py propose`; the skill changes only on an explicit request.

## Verification

The skill is working when this scenario completes with real evidence:

1. Two independent mutating tasks are planned with measurable acceptance criteria.
2. Repository and Herdr runtime are inspected; base branch/commit recorded.
3. Each mutating task has a validated, persisted contract with a digest, a write scope and a declared
   mutation policy.
4. Two isolated worktrees exist, with their IDs captured from command output.
5. Two workers are started and their cwd **and** branch verified against each worktree.
6. Both prompts (carrying the contracts) are dispatched before any wait, and overlapping `working`
   states are observed.
7. Guards are installed per worktree (`scope_guard_installed` recorded); any claimed prevention is
   proven in force, otherwise it is recorded as `scope_violation`-only detection.
8. Both outputs are collected, the result contracts collected, and each diff/commit/scope
   independently verified (`orch.py verify`).
9. An independent read-only reviewer receives the review package and returns a structured VERDICT per
   task.
10. A FAIL is returned to the responsible worker and re-reviewed (bounded cycles).
11. The merge gate is `ready: true` for each integrated branch, and any bypass is logged
    (`merge_gate_bypassed` + a `decisions.md` line).
12. Scope validation is `PASS` for every integrated branch; a hypothetical out-of-scope path would
    have produced `SCOPE: FAIL` and blocked the merge.
13. Final validation runs on the integration branch; commits verified reachable.
14. State (including contracts, checkpoints, scope verdicts and gates) is persisted, and a new session
    reconstructs the run state from Git + Herdr + state.
15. A long task has a checkpoint that a resumed or replacement worker can act on, and the replacement
    receives a reconstructed package rather than "continue where the other one stopped".
16. The watchdog classifies a real runtime sample, and no decision was made by the watchdog itself.
17. Owned resources are cleaned or explicitly listed as remaining.
18. The three configuration axes are resolved, persisted, and re-read correctly after a restart.
19. Every worker's observed argv shows the intended autonomous launch (`herdr pane process-info`).
20. An explicit user team constraint (for example a single agent kind) is honoured, with no silent
    substitution of the pinned kind.
21. Lessons found during the run exist as proposals in `.orchestrator/skill-proposals.md` and the
    skill files are unchanged by the run.
22. A worker with visible pane activity and no file change is classified `spinning`, with
    `seconds_since_write` and `spin_after` visible in the sample.
23. A field-level `contract --force` call keeps every field it did not mention, and `--file` names the
    fields it is about to drop.
24. `orch.py resume --id <task>` diagnoses a lost worktree and `--recreate` rebuilds it from the
    recorded branch; the replacement receives that package.
25. When the installed binary rejects the write-boundary environment, `guard --plan` reports
    `prevention: none` with the reason, and no worker is launched with that environment.
26. The bootstrap checked the repository for a foreign orchestrator (`ao/*` branches, another tool's
    worktrees, a second orchestrator process) before the first mutating dispatch.

If any of those steps cannot be evidenced with real output, the run is not complete.

## References

- `references/herdr-cli-contract.md` — verified command groups, JSON shapes, ID rules, state
  semantics, exit codes, safety rules of the CLI itself.
- `references/execution-playbook.md` — decomposition, DAG, worktree policy and naming, cwd
  verification, non-blocking dispatch, mechanical monitoring, blocked classification, commit policy,
  scope protection, provider failure and worker replacement, non-Git tasks, large refactors.
- `references/task-contracts.md` — the contract schema and validation, where the contract is used,
  the result contract, the DIRECT-vs-delegated boundary, and the full role-policy table.
- `references/scope-enforcement.md` — Layer A prevention mechanisms (with the evidence and their
  boundaries), Layer B detection and the scope validator, violation handling, honest limitations.
- `references/checkpoints-and-resume.md` — when checkpoints are justified, the checkpoint schema,
  resume after an interruption, the replacement protocol and its failure budgets.
- `references/watchdog-and-events.md` — control vs data plane, watchdog signals, classification table,
  conservative stall detection, thresholds, and the structured event model.
- `references/coordination-modes.md` — `assisted` / `supervised_auto` / `auto`, the checkpoint table,
  escalation triggers, non-negotiables, how to record a mode change.
- `references/team-composition.md` — `manual` / `semi_auto` / `auto`, `team_constraints`, the bootstrap
  resolution procedure, selection heuristics, and the explicit "no cost/model scoring yet" boundary.
- `references/worker-execution-modes.md` — `autonomous` / `interactive`, the scope limits, the per-kind
  discovery procedure, the verified invocation table, and post-spawn argv verification.
- `references/self-modification.md` — proposals vs edits, when the skill may change, the change
  procedure and its guardrails.
- `references/quality-and-integration.md` — testing stage, contract-driven reviewer independence, fix
  loop, merge gate, integration, final validation, cleanup, cancellation, pause/resume, completion.
- `references/prompts.md` — delegation (contract-based), research, review package, fix, checkpoint,
  replacement, recovery and report templates.
- `references/state-and-recovery.md` — state.json / tasks.json / events.jsonl schemas (v1 -> v3), atomic
  writes, the five-step recovery protocol and reconciliation table.
- `references/defaults-and-antipatterns.md` — the recommended default policy block (contracts, scope,
  checkpoints, watchdog, merge gate) and the full anti-pattern list.
- `scripts/orch.py` — stdlib-only state manager and contract/gate CLI (init/add-task/set-task/
  set-modes/modes/propose/contract/result/verify/validate-scope/merge-gate/guard/checkpoint/
  replace-worker/review-package/events/event/ready/status/reconcile/validate/report).
- `scripts/contracts.py` — contract, result and checkpoint schemas plus the deterministic merge gate
  (pure functions; imported by every other script).
- `scripts/scope_guard.py` — glob matching, scope classification, git diff comparison, the run-owned
  commit gate and the per-kind prevention adapters.
- `scripts/watchdog.py` — deterministic runtime watchdog (signals, classifications, events).
- `scripts/events.py` — the shared append-only event log (flock, run_id, secret redaction).
- `scripts/test_orch.py` — stdlib unittest suite for the state manager, contracts, scope enforcement,
  merge gate, checkpoints, replacement, migration and events.
- `scripts/test_watchdog.py` — stdlib unittest suite for the watchdog (fake Herdr, temp repos only).
- `scripts/validate_skill.py` — frontmatter, reference-link and required-section validation for this
  skill; run it after any edit to the skill.
