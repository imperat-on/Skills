# Checkpoints, resume and worker replacement

A worker that worked for a long time must not start over because a process died, a provider failed,
a CLI closed, a context blew up, a pane disappeared or the session was restarted. Checkpoints plus a
reconstruction protocol make recovery keep the work instead of rediscovering it.

## When checkpoints are justified

The orchestrator decides, from the contract: `checkpoint_policy: auto | required | none`.

- `auto` (default) - long/complex work: several acceptance criteria, a declared `phase_plan` with
  more than one phase, or a multi-stage migration/refactor;
- `required` - the contract says so explicitly;
- `none` - small, single-commit tasks. Never generate checkpoints (or forty tiny commits) for a task
  that fits in one step.

Checkpoints go at meaningful transitions (a phase completed, a decision taken), not on a timer.
`orch.py contract` prints whether checkpoints are required so the scheduler knows before dispatch.

## Checkpoint content

Persisted in `.orchestrator/checkpoints/<task-id>.json` (never inside the project tree), with the
previous snapshot archived to `<task-id>.history.jsonl`:

```yaml
checkpoint:
  task_id: backend-refactor
  phase: 3
  total_phases: 5
  completed:
    - schema updated
    - service layer migrated
  current:
    - API integration
  remaining:
    - tests
    - cleanup
  last_known_commit: <sha>
  changed_files: []
  decisions:
    - kept the old API route for compatibility
  blockers: []
  worker: backend_worker
```

Written by the worker itself (the prompt tells it the absolute path of `scripts/orch.py`):

```bash
python3 <skill>/scripts/orch.py --repo-root <repo> checkpoint --id <task> --set \
  --phase 3 --total-phases 5 \
  --completed "schema updated" --completed "service layer migrated" \
  --current "API integration" --remaining "tests" --remaining "cleanup" \
  --commit <sha>
```

or from a file (`--file cp.yaml`) for a structured snapshot. `--show`/`--list` read it back. Invalid
checkpoints (phase > total_phases, no task id) are refused with exit code 2.

Interim commits are a separate decision: commit when the work is in a coherent, reviewable state.
Checkpoints are cheap state, commits are history - do not confuse the two, and never spam commits
just to have checkpoints.

## Resume after an interruption

Session lost, but the run is alive:

1. `orch.py reconcile` - persisted state vs Git + Herdr reality; discrepancies only;
2. `orch.py checkpoint --id <task> --show` - the worker's own last known position;
3. `git -C <worktree> status --short --branch`, `log --oneline <base>..<branch>`,
   `diff --name-only <base>...<branch>` - what actually exists;
4. `orch.py validate-scope --id <task>` - is what exists still inside the contract?
5. resume the same worker with the recovery prompt (contract + rebuilt state + remaining work).

Never tell a resumed or replacement worker "continue where the other one stopped" without
reconstructing the state for it: that phrase hides an unknown amount of missing work.

## Replacement worker

```text
worker original
        v
failure / death / provider unavailable
        v
Hermes: git + checkpoint + state + scope  (reconstruct, do not assume)
        v
classify the existing work: done / partial / untouched / violating
        v
spawn the replacement - one writer per worktree, verified before dispatch
        v
replacement receives: contract, worktree, branch, verified commit/diff, latest checkpoint,
                      remaining work, existing findings/verdict
```

```bash
python3 scripts/orch.py --repo-root <repo> replace-worker \
  --id <task> --agent <new-worker> --old-agent <old-worker> --pane <pane> \
  --reason "provider 503 after 3 retries"
```

The command:

- refuses to proceed while the previous agent still looks live in `herdr agent list` (two writers in
  one worktree corrupt each other) unless `--force`, which is recorded as a decision;
- appends to `worker_history` (agent, pane, workspace, kind, reason, last checkpoint phase, last
  commit, was it still live) and increments `replacement_count`, keeping `current_worker` current;
- re-derives reality from Git (commit, changed files, worktree cleanliness, scope) and prints a full
  reconstruction package (also written to `.orchestrator/reports/<task>-replacement-N.txt`):
  contract, branch/base/commits, changed files, scope status, latest checkpoint, remaining work,
  existing findings/verdict, and the explicit "one writer per worktree" rule.

Hard rules for replacement:

- the replacement stays on the **same branch and worktree** - existing work is preserved;
- do not redo completed work; the package states what already exists;
- never reuse a worktree whose previous writer might still be running;
- if the failure is a provider/configuration failure (not a task failure), record it separately and
  do not treat it as an implementation failure: `404 unsupported model` is a configuration problem,
  not something to retry in a loop;
- bounded budgets: `provider_error: 2`, `worker_task_failure: 2`; escalate instead of an endless
  replacement chain.
