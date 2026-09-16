# Persistent state and recovery

State exists so a lost session can rebuild reality — not so the orchestrator can trust itself later.
Git, the filesystem and the Herdr runtime always win over the files here.

## Layout

```text
.orchestrator/
  state.json      run identity, repo facts, run configuration, watchdog thresholds, owned resources
  tasks.json      the task graph with live status, agent, worktree, branch, commit, launch mode,
                  contract, result, checkpoint, scope validation, merge gate, worker history
  decisions.md    human-readable decisions (trust grants, mode changes, workarounds, escalations)
  events.jsonl    append-only structured transition log (shared with the watchdog)
  contracts/      <task-id>.json - the structured task contract (the delegation yardstick)
  checkpoints/    <task-id>.json + <task-id>.history.jsonl - worker progress for long tasks
  guards/         <task-id>/ - run-owned scope guards (pre-commit gate, per-kind prevention plan)
  reports/        captured test output, review packages, replacement packages, run reports
  watchdog/       last_sample.json - the last mechanical runtime picture
  skill-proposals.md   candidate lessons about this skill (recorded, never auto-applied)
```

Project-local state must not be committed. Add `.orchestrator/` to `.git/info/exclude` — never to
`.gitignore`, and never modify project ignore rules without explicit approval. `scripts/orch.py init`
does this and records the decision in `decisions.md`.

**Secrets never go here.** No tokens, keys, passwords, cookies or provider credentials in any of
these files, or in prompts, commits, logs or reports. Use the environment/credential store instead.

## state.json

```json
{
  "version": 3,
  "run_id": "20260914-034800-refactor-auth",
  "created_at": "ISO-8601",
  "updated_at": "ISO-8601",
  "status": "running",
  "coordination_mode": "supervised_auto",
  "team_mode": "semi_auto",
  "worker_execution_mode": "autonomous",
  "team_constraints": {
    "allowed_agent_kinds": [],
    "pinned_roles": {},
    "max_workers": null,
    "notes": []
  },
  "watchdog": { "stall_after": 900, "dead_grace": 60, "idle_grace": 60 },
  "migration": { "from_version": 2, "migrated_at": "ISO-8601", "note": "..." },
  "repo": {
    "root": "/path/to/repo",
    "base_branch": "main",
    "base_commit": "sha",
    "integration_checkout": "/path/to/repo"
  },
  "orchestrator": { "agent_name": "hermes", "workspace": "w1", "pane": "w1:p1" },
  "resources": {
    "owned_agents": [], "owned_workspaces": [], "owned_panes": [],
    "owned_worktrees": [], "owned_branches": []
  },
  "tasks": [],
  "integration": { "completed": [], "pending": [] }
}
```

`status` is one of `running`, `paused`, `cancelled`, `success`, `partial`, `failed`. `resources` is
the ownership ledger: the only things cleanup may touch. `watchdog` holds the conservative stall
thresholds read by `scripts/watchdog.py`.

Version history: `1` (no run configuration) -> `2` (three axes + team constraints) -> `3` (contracts,
checkpoints, scope validation, merge gate, worker history, watchdog thresholds). A state file from an
older version is normalised **in memory** on read - nothing is dropped, missing keys get safe defaults
- and reported by `orch.py validate` as a warning; the normalised values are persisted on the next
write (`set-modes`, `contract`, `checkpoint`, `verify`, `report`, ...). Missing task fields are
defaulted the same way (`contract`, `result`, `checkpoint`, `scope_validation`, `merge_gate`,
`worker_history`, `replacement_count`, `last_activity`).

The run configuration (`coordination_mode`, `team_mode`, `worker_execution_mode`, `team_constraints`)
belongs to the run identity, not to a single session: `orch.py modes` prints it, `orch.py set-modes`
changes it (logging a `mode_changed` event and a `decisions.md` line), and a resumed run re-applies it.
A legacy state file without those keys is migrated in memory to the defaults on read and reported by
`orch.py validate`; persisting them takes one `set-modes` call. An explicit instruction from the user in
the current session outranks the persisted values (precedence level 2 over level 3) - record the change
rather than silently diverging.

## tasks.json

```json
{"tasks": [
  {
    "id": "frontend", "title": "Implement frontend", "status": "working", "role": "worker",
    "agent": "frontend_worker", "workspace": "w3", "pane": "w3:p1",
    "worktree": "/path/.herdr-worktrees/repo/run/frontend", "branch": "agent/run/frontend",
    "base_commit": "abc123", "commit": null, "depends_on": [],
    "mutates_files": true,
    "expected_scope": ["src/ui"],
    "acceptance": ["UI behaves correctly", "tests pass"],
    "preferred_agent_kind": "auto", "worktree_required": true,
    "worker_execution": {
      "mode": "autonomous", "kind": "opencode", "args": ["--auto"],
      "verified_after_spawn": true
    },
    "contract": { "...": "the full structured contract (see task-contracts.md)" },
    "contract_digest": "9f2c1ab77e0d4c31",
    "result": { "result": "DONE", "commit": "abc123", "changed_files": [], "tests": [] },
    "checkpoint": { "phase": 3, "total_phases": 5, "remaining": ["tests"], "blockers": [] },
    "scope_validation": { "status": "PASS", "unexpected": [], "forbidden": [], "violations": [] },
    "merge_gate": { "ready": false, "fields": {}, "reasons": ["review=missing"] },
    "verification": { "commands": [], "commit_exists": true, "worktree_clean": true },
    "tests": { "status": "pass", "command": "pytest -q", "evidence": "reports/frontend-tests.txt" },
    "worktree_clean": true, "changed_files": ["src/ui/Button.tsx"], "blockers": [],
    "fix_cycles_open": 0,
    "worker_history": [{"agent": "frontend_worker", "reason": "provider 503", "replaced_at": "ISO"}],
    "current_worker": {"agent": "frontend_worker_2", "since": "ISO"},
    "replacement_count": 1,
    "last_activity": "ISO-8601",
    "verified": null, "verdict": null, "notes": []
  }
]}
```

Statuses: `pending`, `ready`, `dispatched`, `working`, `blocked`, `review`, `failed`, `needs_fix`,
`passed`, `integrated`, `cancelled`. A task is `ready` only when every `depends_on` entry is
`passed`/`integrated` **and** its contract is valid (`orch.py ready` enforces both, and prints
`TASK_CONTRACT_INVALID` for mutating tasks that cannot be delegated yet).

Contract, checkpoint, scope and gate fields are what a resumed session reconstructs the run from: the
contract (with its digest) is the yardstick, the checkpoint is the worker's last known position, the
scope validation is the mechanical truth about the diff, and the gate says whether the branch is
technically eligible for integration. None of them replaces Git and the runtime as ground truth.

Write state atomically (write a temp file in the same directory, then rename) so a crash mid-write
cannot corrupt the only copy. `scripts/orch.py` does this for every mutation.

## events.jsonl

One JSON object per line, append-only:

```json
{"time":"ISO-8601","event":"worker_started","task":"frontend","agent":"frontend_worker"}
{"time":"ISO-8601","event":"task_blocked","task":"backend","reason":"permission_gate"}
{"time":"ISO-8601","event":"commit_created","task":"frontend","commit":"abc123"}
{"time":"ISO-8601","event":"review_passed","task":"frontend"}
{"time":"ISO-8601","event":"merged","task":"frontend"}
{"time":"ISO-8601","event":"cleanup_completed","resource":"w3"}
```

Log at least: task created, worktree created, agent started, task dispatched, task blocked, commit
detected, tests run, review completed, fix cycle, merged, final validation, cleanup, pause/cancel.
This log is what makes recovery and audit possible.

## Recovery protocol

### Rebuilding a vanished worktree

Git reality outlives the filesystem: a deleted worktree still has its commits in the repository, so
recovery starts there instead of creating a new branch.

```bash
python3 scripts/orch.py resume --id <task>             # read-only diagnosis + reconstructed package
python3 scripts/orch.py resume --id <task> --recreate  # git worktree add the branch at the run path
```

`resume` reports whether the recorded path and the branch still exist, the commits since `base_commit`,
the changed files, the latest checkpoint and the remaining acceptance criteria. That package is what a
replacement worker receives - never "continue where the other one stopped".

The five steps, in order, with no mutation before step 5.

1. **Detect project state** — `read_file('.orchestrator/state.json')` if present.
2. **Inspect live Herdr runtime** — `herdr agent list`; `herdr workspace list`; `herdr worktree list
   --cwd <repo-root>`; `herdr api snapshot` for the full picture. Note which recorded agents,
   workspaces and worktrees are actually alive.
3. **Inspect Git reality** — `git worktree list`; `git branch --all`; `git status --short --branch`;
   `git log --graph --oneline --decorate -20`.
4. **Reconcile** — compare the three sources; the runtime wins. Mark stale resources and decide per
task. `orch.py reconcile` also checks the contract against the uncommitted worktree paths (reporting
`SCOPE_VIOLATION` before anything is committed), flags mutating tasks without a valid contract, and
compares checkpoints with the recorded commit.
5. **Resume** — continue only what is safely reconstructible; ask the user when ambiguity could cause
   duplicate work or a destructive action. Before re-dispatching a mutating task, confirm its contract
   is still valid, its scope validation still passes and its guards are installed; before re-dispatching
   after a death, use `orch.py replace-worker` so the new worker receives the reconstructed state and
   the latest checkpoint (`references/checkpoints-and-resume.md`).

Reconciliation table:

| Persisted | Observed | Classification | Action |
|---|---|---|---|
| agent `working` | agent missing from `agent list` | interrupted | inspect worktree + commits + checkpoint, then replace the worker |
| agent `working` | alive, no output/commit for > `stall_after` | stalled | inspect; if the process is alive and silent, re-prompt or replace |
| agent `working` | pane/workspace gone, or the worktree path gone | dead / stale | rebuild from git + checkpoint, then `replace-worker` |
| worktree path recorded | path missing on disk | stale resource | drop from ownership ledger, log the event |
| commit pending | branch already merged into the base | integrated | mark `integrated`, skip re-merge |
| task `dispatched` | agent idle with no commit and no diff | stalled | read output, re-prompt with the recovery prompt |
| task `review` | reviewer agent gone | interrupted | start a new reviewer, hand over the review package |
| checkpoint phase N | commit newer than the checkpoint | progress not yet checkpointed | refresh the checkpoint from git before replacement |
| gate `ready: false` | task marked `integrated` | gate bypassed | `orch.py validate` flags it; report the bypass |
| status `paused`/`cancelled` | resources alive | intentional | report them; do not clean without user consent |

`scripts/orch.py reconcile` mechanizes this: it prints only the discrepancies between persisted state
and Git/Herdr reality, never modifying anything.

## Cross-session guarantees

- A new session can rebuild the run from `.orchestrator/` + `git` + `herdr`, even if no context
  survives.
- The three configuration axes and the team constraints survive recovery, so a resumed `assisted` run
  keeps asking for approvals and a resumed run with `team_constraints.allowed_agent_kinds: [opencode]`
  keeps honouring that restriction.
- Lessons recorded as proposals survive too, and are never applied automatically.
- Nothing in the state files is trusted without a matching live observation.
- Ownership is explicit, so cleanup after a restart still cannot touch another client's resources.
