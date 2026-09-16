# Quality, integration and lifecycle

Independent review, the fix loop, integration, final validation, cleanup, cancellation and the
definition of done. The orchestrator owns all of this; workers never mark their own work accepted.

## Independent review

Every mutating task gets an independent review, judged against the **same task contract** the worker
was given. The reviewer's inputs are serialized deterministically by

```bash
python3 scripts/orch.py --repo-root <repo> review-package --id <task> [--live]
```

which emits (and writes to `.orchestrator/reports/<task>-review-package.txt`) the original contract,
base commit, worker commit and branch, changed files, scope validation, acceptance criteria, required
checks and the recorded test evidence - with the read-only instruction and the required verdict shape.
A review without the original contract is not independent review, it is opinion.

Place the reviewer in a read-only environment: it must not edit code unless it is explicitly
reassigned as fixer. Use a different agent kind or model than the implementer whenever one is
available; the reviewer must inspect the diff, the commit, the tests and the architecture implications
rather than trusting the worker's claims.

Required reviewer output (structured, so the orchestrator can act on it mechanically):

```yaml
verdict: PASS | FAIL

blocking_findings: []      # actionable, referenced to file/behaviour; required when FAIL
non_blocking_notes: []
scope_findings: []
acceptance:
  <criterion>: PASS | FAIL
```

The reviewer checks CORRECTNESS, SCOPE, ACCEPTANCE, REGRESSIONS and UNRELATED_CHANGES. A FAIL verdict
without actionable findings is not usable - ask for specifics rather than relaying a vague verdict.
`verdict: PASS` is what the merge gate reads; it is recorded on the task with
`set-task --verdict PASS` (and `review_passed`/`review_failed` in the event log).

## Fix loop

```text
review FAIL
   -> extract actionable findings (specific, referenced to file/line/behaviour)
   -> send them to the responsible worker (same worktree, same branch)
   -> worker fixes and commits the fix
   -> tests
   -> independent review again
```

Budget `max_fix_cycles: 3`. If the same finding keeps failing, escalate to the user with the history
instead of looping. Findings go back to the author of the work, not to the orchestrator.

## Testing stage

Testing may happen inside each worker branch, in a dedicated tester workspace, after integration, or
all of the above for high-risk work. Minimum: task-local tests before a worker completes, and
integration tests after merge. Never claim tests passed unless command output was observed. Capture
per test run:

```text
command
exit code
key output
duration (when relevant)
```

Store the captured evidence under `.orchestrator/reports/` and reference it from state.

## Integration

Under `coordination_mode: assisted`, ask before each merge; under `supervised_auto`/`auto`, merge and
report it at the next checkpoint. (See `references/coordination-modes.md`.)

```bash
git -C <integration-checkout> status --short --branch     # must be clean
```

Require a clean integration checkout unless the user explicitly accepts otherwise. Default strategy:

```bash
git merge --no-ff <worker-branch>
```

unless the repository's own policy specifies something else. Integrate one branch at a time, in
dependency order. After every merge: inspect merge output, inspect status, run relevant tests.

**On conflict: STOP.** Record the conflict, inspect the affected files, and present the situation to
the user (or run a dedicated conflict workflow only if explicitly authorized). Never invent an
automatic resolution.

## Orchestrator-side validation before merge: the merge gate

The gate is computed deterministically, not judged: `orch.py merge-gate --id <task> [--live]` reads
the contract, the collected result, the recorded scope validation, the test evidence, the review
verdict, the worktree state and the commit, and prints/persists:

```yaml
merge_gate:
  contract: pass
  result: collected
  scope: pass
  tests: pass
  review: pass
  worktree: clean
  commit: present
  blockers: none
  fix_cycles: closed
  ready: true
```

A branch may only be integrated when **every** field holds. `ready: false` means **do not merge** -
return the work to the responsible worker (or record an explicit, logged escalation).

`set-task --status integrated` re-evaluates the gate and **refuses** while it is not ready; only
`--force --note "<reason>"` bypasses it, which logs `merge_gate_bypassed` and writes the reason to
`decisions.md`. `orch.py validate` additionally flags any task marked `integrated` whose stored gate
was not ready. The orchestrator cannot ignore the gate on subjective grounds - "it looks good" is not
a gate field.

## Final validation

```bash
git status --short --branch
git log --graph --oneline --decorate -20
git merge-base --is-ancestor <worker-commit> HEAD     # per integrated worker commit
```

Then run the project's own validation: tests, lint, typecheck, build, smoke test, security checks as
applicable. Only after validation does the run count as successful.

## Cleanup

Cleanup is its own stage and must be safe. Never remove resources before successful integration and
final verification. Under `coordination_mode: assisted`, ask before removing anything; under
`supervised_auto`/`auto`, clean up and report what was removed. For resources owned by the current run:

1. confirm the worker is no longer needed;
2. confirm the branch is integrated or intentionally abandoned;
3. confirm the worktree has no uncommitted changes;
4. stop the owned agent if appropriate;
5. remove the owned worktree (`herdr worktree remove --workspace <owned-ws-id>`);
6. delete the merged temporary branch if policy permits;
7. close owned empty panes/workspaces when safe (`herdr pane close <owned-pane-id>`).

Never delete branches or worktrees merely because they look old, and never close or kill anything the
run did not create. Anything left behind is listed explicitly in the final report.

## Cancellation

If the user cancels: stop new dispatch; determine which workers are still active; avoid killing
processes that may hold valuable uncommitted work without inspecting them first; capture current Git
state; persist the run as `cancelled` (or `paused` if the user intends to continue); and explain
which resources remain and what they hold.

## Pause and resume

Pausing is intentional: set `status: paused`, do not clean resources automatically. On resume, run the
full recovery protocol before touching anything.

## Recovery (summary)

Run on every new session before assuming prior state is gone:

1. **Detect project state** — look for `.orchestrator/state.json`.
2. **Inspect live Herdr runtime** — `herdr agent list`, `herdr workspace list`,
   `herdr worktree list --cwd <repo-root>`, `herdr api snapshot`.
3. **Inspect Git reality** — `git worktree list`, `git branch --all`,
   `git status --short --branch`, `git log --graph --oneline --decorate -20`.
4. **Reconcile** — never trust state files blindly; filesystem, Git and Herdr are authoritative.
   Mark stale resources, e.g.: state says an agent is working but it no longer exists -> interrupted;
   state says a worktree exists but the path is gone -> stale; state says a commit is pending but the
   branch is already merged -> integrated.
5. **Resume** — continue only tasks that can be safely reconstructed. If ambiguity could cause
   duplicate work or a destructive action, ask the user.

`scripts/orch.py reconcile` performs steps 1-4 mechanically and prints only discrepancies.

## Crash tolerance

Design for: Hermes session restart, worker crash, terminal close, provider outage, model error,
machine reboot, partial integration. Persist state immediately after each of: task created, worktree
created, agent started, task dispatched, commit detected, review completed, merge completed, cleanup
completed.

## User-intervention thresholds

Ask the user when: a security/trust decision is new; a merge conflict needs judgement; the requested
scope materially changes (including an unavailable agent kind the user pinned); destructive cleanup is
uncertain; provider credentials are missing; the architecture has multiple high-impact choices; or
recovery state is ambiguous. These are the escalation triggers of every coordination mode, `auto`
included - see `references/coordination-modes.md`. Do not ask for routine confirmations that the
resolved mode already covers.

## Progress communication

For long runs, report concise status at human-scale intervals, never a stream of shell commands:

```text
2/5 tasks done
frontend: done
backend: working
tests: waiting on backend
review: pending
```

## Completion definition

A run is complete only when: all required tasks are resolved; accepted implementations were
reviewed; required tests passed with observed output; integration completed when requested; final
validation passed; state is persisted; the user received a concise report; and cleanup was handled
according to policy.

## Final run report

```text
RESULT: SUCCESS | PARTIAL | FAILED

Run configuration: coordination=<mode> team=<mode> workers=<mode>

Tasks:
Integrated commits:
Tests:
Review:
Outstanding risks:
Resources remaining:
Cleanup performed:
```

`scripts/orch.py report` renders this skeleton from persisted state so the report cannot drift from
the evidence.
