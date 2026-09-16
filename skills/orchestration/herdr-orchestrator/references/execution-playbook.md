# Execution playbook

Decomposition, isolation, dispatch, monitoring and independent verification. Every rule here is
applied by the orchestrator; workers only see their own slice.

## Task graph

Before spawning anything, write the graph. Each task:

```yaml
id: stable-local-id            # sanitized, filesystem- and branch-safe
title: concise description
role: worker | researcher | tester | reviewer | fixer
status: pending
depends_on: []                  # ids; a task is ready only when all are satisfied
mutates_files: true | false
expected_scope:                  # files/directories/components it may touch
  - path/or/component
acceptance:                     # measurable criteria, at least one
  - observable, checkable statement
preferred_agent_kind: auto      # resolved from herdr agent list at dispatch time
worktree_required: auto         # true for mutating tasks on a dirty-shared-repo risk
```

Statuses: `pending`, `ready`, `dispatched`, `working`, `blocked`, `review`, `failed`, `needs_fix`,
`passed`, `integrated`, `cancelled`.

DAG shape matters more than agent count:

```text
          research
         /        \
        v          v
    task_a      task_b
        \          /
         v        v
       integration
           |
           v
         tests
           |
           v
        review
```

Schedule every node whose dependencies are satisfied. "Multiple agents exist" is not a reason to
parallelize; only true independence is.

### Dynamic task creation

Evidence can create tasks mid-run: reviewer finds a bug -> fixer; test finds a regression ->
diagnosis; worker finds a missing migration -> migration task; implementation exposes an unknown API
-> research task. Every dynamically created task is recorded in state and in the event log, and gets
the same acceptance criteria and scope discipline as the planned ones.

## Repository detection

```bash
git rev-parse --show-toplevel
git status --short --branch
git rev-parse HEAD
git branch --show-current
git worktree list
git branch --all
```

Determine repo root, base branch, base commit, dirty state, existing worktrees and existing branches.
Never assume `main` or `master`. If the current checkout is dirty, it is not a safe integration base —
record the pre-run state and either stash deliberately (only with user awareness) or integrate in a
separate clean checkout.

## Worktree policy and naming

Put every worktree inside the run area - `<repo>/.orchestrator/worktrees/<run-id>/<task-id>` - and record
that root in `state.json` as `worktree_root`. A checkout beside the repository (`<parent>/<repo>-<task>`)
looks like scratch to the user, who is entitled to delete it: doing so removes the worker's uncommitted
work AND its pane/agent, ending the run without any error. If that already happened,
`orch.py resume --id <task>` prints the reconstructed package and `--recreate` rebuilds the worktree from
the recorded branch at the canonical path.

Default: one worktree per independent mutating task or worker. Multiple mutating workers must never
share a checkout.

```bash
herdr worktree create --cwd <repo-root> --branch <task-branch> --base <base-ref> \
  --path <worktree-path> --label <task-id> --no-focus
```

Recommended naming (sanitize `task-id`: lowercase, `[a-z0-9-]`, no slashes):

```text
branch:      agent/<run-id>/<task-id>
worktree:    <repo-parent>/.herdr-worktrees/<repo-name>/<run-id>/<task-id>
```

If repository policy forbids hidden sibling directories, use an explicit external temp path instead
and record it in state. Never reuse a branch that already contains unrelated work. Read-only tasks
(research, log inspection, benchmarking, environment diagnosis) normally need no worktree: a scratch
pane or workspace whose cwd is a throwaway directory is enough, and it avoids pointless Git setup.

Record from the `worktree_created` response: workspace ID, tab ID, root pane ID, worktree path.

## Placement and cwd verification

```bash
herdr agent start <agent-name> --kind <kind> --pane <root-pane-id> -- <autonomous-args>
herdr pane process-info --pane <root-pane-id>     # observed argv: the autonomous launch, verified
herdr pane get <root-pane-id>
herdr agent get <agent-name>
git -C <worktree-path> branch --show-current
git -C <worktree-path> rev-parse HEAD
```

Check both `cwd` and `foreground_cwd` on the pane and on the agent, and the worktree's actual branch
and HEAD. Do **not** delegate mutating work until cwd and branch are correct. A wrong cwd means the
worker will edit the wrong tree — fix the placement first.

If a kind fails to become ready in a pane on this host, remember the pane-level fallback: launch the
agent by hand (`herdr pane run <pane> "<agent-cli>"`), wait, confirm with
`herdr pane read <pane> --source detection --lines 40`, then `herdr agent rename <pane> <name>` so it
becomes addressable by name. Record the workaround in the run's `decisions.md`.

Reviewer placement caveat: a read-only reviewer parked in a plain scratch directory can be blocked by
the agent CLI's own sandbox the moment it reads or runs a command against the task worktree outside
its cwd (observed as `blocked` with an "access external directory" permission dialog). Do not approve
that dialog on your own authority. Either place the reviewer's cwd inside the tree it reviews, or give
it a self-contained read-only copy of the repository checked out at the exact commit under review
inside its own cwd (`git clone --no-hardlinks <repo> <reviewer-cwd>/repo && git checkout <commit>`)
and instruct it to work only inside its cwd. The copy also guarantees it cannot contaminate the
worker's branch. Verify afterwards that the copied checkout and the worker worktree HEAD are unchanged.

## Delegation contract

Every implementation prompt carries the **structured task contract**: objective; exact
worktree/repository context; `write_scope`; `forbidden_scope`; acceptance criteria; required checks;
deliverables; mutation policy; what to do when blocked; the checkpoint rule; the requirement to commit
its own focused commit; and the **result contract** shape to answer in. Write the contract first
(`orch.py contract`, see `references/task-contracts.md`), then render it into the prompt with
`references/prompts.md`. Keep prompts scoped: no worker receives the whole conversation.

Before dispatching a mutating task, install and verify its guards
(`orch.py guard --install-hook [--plan] [--verify-launch]`, see `references/scope-enforcement.md`).
The worker may not change its own contract; a material change is an orchestrator decision recorded
with `contract --force` and a reason.

Two things are decided before the prompt, not inside it: **who** is on the team (`team_mode`, see
`references/team-composition.md`) and **how** the worker is launched (`worker_execution_mode`, see
`references/worker-execution-modes.md`). Record the launch (`--launch-mode`, `--launch-kind`,
`--launch-arg`, `--launch-verified`) on the task before delegating.

## Non-blocking parallel dispatch

Dispatch all ready tasks before waiting for any of them.

```bash
# correct: submit everything, then monitor
herdr agent prompt worker_a "<task a>"
herdr agent prompt worker_b "<task b>"
herdr agent prompt worker_c "<task c>"
# then: herdr agent get / read / wait on each
```

Never the sequential shape (`prompt A --wait`, wait, `prompt B`). Use `--wait` only when
serialization is intentional and you have said why. Corroborate real concurrency the way it can be
proven: overlapping `working` states across `herdr agent list` samples and independent commits in
isolated worktrees.

## Monitoring loop

Monitoring is **mechanical first**: run the deterministic watchdog instead of polling with reasoning.
`scripts/watchdog.py` samples the Herdr state, the agent output, the pane/workspace/worktree
existence, git history and checkpoints, classifies each task (healthy / working / stalled / blocked /
process_dead / agent_gone / pane_missing / workspace_missing / worktree_missing / scope_violation /
idle / done / unknown) and appends structured events.

```bash
python3 scripts/watchdog.py --repo-root <repo> --json      # one compact sample for this decision point
```

Sample at human-scale intervals (60-180s, or at phase boundaries), never in a tight loop, and act only
on what the classification says needs the orchestrator. Details, thresholds and the event model:
`references/watchdog-and-events.md`.

When you do need the raw picture, read it yourself:

```text
agent | task | state | workspace | pane | branch | last event
```

Sources: `herdr agent list` (all agents at once), `herdr agent get <agent>` (one), `herdr agent read
<agent> --source recent-unwrapped --lines N` (output), `herdr agent explain <agent>` (why a state was
classified). React to transitions:

```text
working  -> keep monitoring
blocked  -> inspect output, classify, resolve
idle/done-> collect the result, verify it, then decide
done     -> (from a non-working state) collect and verify
unknown  -> investigate with get/read/explain before concluding anything
```

## Blocked handling

1. Read the current output. 2. Determine why. 3. Classify:

```text
safe-known              -> already authorized by policy; resolve and continue
user-approval-required  -> ask the user
agent-error             -> treat as a worker failure (see below)
credential/provider      -> separate failure class, ask or reconfigure
ambiguous               -> ask the user
```

Typical `user-approval-required` causes: trusting a repository, trusting a hook, a destructive
operation, sudo/privilege escalation, a credential request, account authentication, or an external
production action. Do not press Enter blindly (`herdr agent send-keys <agent> enter` is a real
action). Never treat `blocked` as completion.

## Worker result verification

Never trust the final message alone. The worker answers in the **result contract**
(`references/task-contracts.md`), which is collected with `orch.py result --id <task>` - but the
result is a claim, not evidence: the orchestrator re-derives reality from git.

```bash
python3 scripts/orch.py --repo-root <repo> verify --id <task>          # git + scope, recorded
```

which runs, in the worker's worktree:

```bash
git -C <worktree> status --short --branch
git -C <worktree> log --oneline <base>..<branch>
git -C <worktree> diff --stat <base>...<branch>
git -C <worktree> diff --name-only <base>...<branch>
git -C <worktree> diff <base>...<branch>
```

Confirm: expected files changed; forbidden files untouched; the commit exists; the worktree is clean
when it should be; no accidental unrelated changes; tests claimed match tests observable. The
`verify` output is compact on purpose (counts, paths, verdicts) - the orchestrator loads diff *bodies*
only when the verdict is ambiguous, so coordinating does not mean carrying the project in context. For
non-Git tasks, verify the artifact or command result directly rather than the description of it.

## Scope protection

Scope is declared in the contract *before* dispatch and enforced in two layers; details and the
verified mechanisms live in `references/scope-enforcement.md`.

- Layer A (prevention): the run-owned commit gate (`orch.py guard --install-hook`) refuses any commit
  containing a path outside `write_scope` or inside `forbidden_scope`; for `opencode` the permission
  rules deny edits outside the scope at sub-path resolution (`guard --plan --verify-launch`).
- Layer B (detection, always): `orch.py validate-scope --id <task>` compares
  `git diff --name-only <base>...<branch>` with the contract and returns `SCOPE: PASS/FAIL`
  (`--json` for machine consumption). `orch.py verify` runs the same comparison together with the git
  verification and records the evidence.

`SCOPE: FAIL` means the task may not be integrated: record the violation, send the task back to the
responsible worker and require a correction or revert. Workers must not touch, without justification:
unrelated configuration, lockfiles (unless necessary), generated files, CI definitions,
secrets/credentials, or unrelated modules. Account for every path in the diff - "it looks good" is not
an argument, and the orchestrator never widens a scope to match the code it received.

## Commit policy

Workers normally commit their own completed changes: clear ownership, isolated history, easy review,
easy rollback, simple integration. One logical task -> one or more focused commits; avoid massive
mixed commits. The orchestrator does not rewrite or amend worker commits unless explicitly required.

## Provider or worker failure

A provider failure is not an orchestration failure. Record it separately (`404 unsupported model`,
`429`, `503`, authentication failure). Then: preserve the worktree; preserve partial work when safe;
optionally start a replacement worker; give the replacement the task plus existing state; do not
redo completed work.

Replacement flow (details: `references/checkpoints-and-resume.md`):

```text
old worker -> capture output + git state -> stop/abandon safely
           -> new worker in the SAME task worktree -> reconstruction package (contract + verified
              state + latest checkpoint + remaining work + findings)
```

```bash
python3 scripts/orch.py --repo-root <repo> replace-worker --id <task> --agent <new> \
  --old-agent <old> --reason "<provider failure | pane gone | stalled>"
```

It refuses to proceed while the old agent still looks live (one writer per worktree), records
`worker_history`/`replacement_count`, and prints the reconstruction package. Never create a second
branch unless it is genuinely necessary, and never hand a replacement the phrase "continue where the
other one stopped" without rebuilding the state for it.

## Failure budget

```yaml
retries:
  provider_error: 2        # bounded; 503 may deserve a retry
  worker_task_failure: 2
  review_fix_cycles: 3
  test_fix_cycles: 3
```

Do not retry deterministic errors blindly: a `404 unsupported model` is a configuration problem, not
something to spam; a syntax or test failure needs actionable feedback, not a rerun.

## Cost and context discipline

Use the strongest reasoning available for architecture, decomposition, difficult debugging, final
review and high-risk decisions; use cheaper capable workers for implementation, repetitive
migrations, tests, documentation and exploration. Never sacrifice correctness for cost.

Give each worker only: task goal, the local architecture/context it needs, its dependencies,
acceptance criteria, constraints, paths/branch, and relevant prior findings. Not the full
conversation — that wastes tokens and contaminates decisions.

## Large refactors

For a large refactor: (1) create an architecture/research task; (2) map the dependency graph;
(3) define boundaries; (4) assign independent components to their own worktrees; (5) define the
integration order; (6) run component tests; (7) review each component; (8) integrate incrementally;
(9) run the full regression suite. Never hand "refactor the entire project" to N workers without
partitioning.

## Non-Git and cross-cutting tasks

Not every task needs a worktree:

```text
scratch pane/workspace -> worker/researcher -> structured report
```

Applies to log inspection, research, documentation lookup, benchmarking and environment diagnosis.

Example topology (frontend/backend can run concurrently only when the API contract is already
defined or the dependency is explicitly handled):

```text
Hermes
  +-- researcher_architecture
  +-- frontend_worker   (worktree agent/<run>/frontend)
  +-- backend_worker    (worktree agent/<run>/backend)
  +-- tests_worker
  +-- reviewer_worker
```
