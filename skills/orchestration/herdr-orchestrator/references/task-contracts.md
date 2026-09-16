# Task contracts, result contracts and role policies

The contract is the unit of delegation. The orchestrator writes it, the worker receives it, the
scope validator, the reviewer and the fix loop all judge against the same object. Free-form prompts
are not a substitute: prose cannot be validated, cannot survive recovery and cannot be diffed
mechanically.

`scripts/contracts.py` owns the schema and the pure logic; `scripts/orch.py contract` writes and
validates it; `scripts/scope_guard.py` consumes the write/forbidden patterns.

## Task contract

Persisted in `.orchestrator/contracts/<task-id>.json` (canonical JSON; a contract file in the small
YAML subset used by this skill is accepted as input) and mirrored in `tasks.json` under `contract`.

```yaml
task_id: frontend-navigation
role: frontend_worker

objective:
  Implement controller navigation in Big Picture.

depends_on: []

write_scope:                  # the only paths this worker may change
  - src/bigpicture/**
  - src/components/controller/**

read_scope:                   # informational; never enforced as a write rule
  - "**"

forbidden_scope:              # denied even when a path also matches write_scope
  - backend/**
  - database/**
  - infra/**

acceptance_criteria:          # the reviewer judges exactly these
  - controller navigation works
  - keyboard navigation remains functional
  - existing tests remain green

required_checks:              # what the worker must run before reporting
  - relevant unit tests
  - typecheck

deliverables:
  - focused commit

branch: agent/<run-id>/frontend-navigation
worktree: <repo-parent>/.herdr-worktrees/<repo>/<run>/frontend-navigation
base_commit: <sha>

worker: frontend_worker        # recorded once the worker exists
agent_kind: opencode           # the kind the worker is launched as

mutation_policy: worktree_only # worktree_only | branch_only | read_only | temp_dirs_only

when_blocked: report the blocked reason to the orchestrator; do not expand scope

# optional
scope_justification: <required only when write_scope is a catch-all>
checkpoint_policy: auto        # auto | required | none
phase_plan: [schema, services, api, tests]
notes: []
```

## Validation before delegation

`orch.py contract --id <id> ...` (or `--file`) validates and refuses to mark anything delegable
while the contract is incomplete. `orch.py ready` hides mutating tasks without a valid contract and
prints `TASK_CONTRACT_INVALID` for them; `set-task --status ready` refuses too.

Required for a **mutating** contract: `role`, `objective`, `write_scope`, `acceptance_criteria`,
`base_commit`, `mutation_policy`. Required for a **read-only** contract: `role`, `objective`.

Errors: unknown role; missing required field; catch-all `write_scope` without
`scope_justification`; unknown `mutation_policy`; unknown `checkpoint_policy`; no
`acceptance_criteria`.
Warnings: no `forbidden_scope`; no `required_checks`; no `worktree` recorded yet; objective too short.

The material fields (`task_id`, `role`, `objective`, `write_scope`, `forbidden_scope`,
`acceptance_criteria`, `required_checks`, `base_commit`, `mutation_policy`, `branch`, `worktree`) are
hashed into a 16-char **digest**. A different digest with the same task means somebody changed the
material terms: `contract` refuses to overwrite without `--force`, and validation flags a digest
mismatch. Contract changes are the orchestrator's decision, never the worker's - the worker cannot
edit the contract and must not reinterpret it.

## Where the contract is used

```text
contract written & validated
        |                     (persisted; digest recorded)
        v
worker prompt  ......... rendered contract + result-contract shape + checkpoint rules
        v
scope validator  ....... write_scope / forbidden_scope vs git diff --name-only base...branch
        v
independent review ..... review-package: contract + base + commit + changed files + scope + tests
        v
merge gate ............. contract valid, scope pass, tests pass, review pass, worktree clean, ...
        v
fix loop ............... findings go back inside the original scope, on the original branch
        v
recovery / replacement . the same contract is handed to the replacement worker
```

## Result contract

The worker's completion report is structured communication, **not evidence**:

```yaml
result: DONE                  # DONE | BLOCKED | FAILED | NEEDS_INPUT
task_id: backend-refactor
commit: <sha>
changed_files: [src/api/routes.ts]
tests:
  - command: npm test -- routes
    exit_code: 0
    result: pass
scope_violations: []
blockers: []
notes: []
```

`orch.py result --id <id> --file <path|->` parses (JSON or the key/value shape), validates and stores
it. `DONE` without `commit`/`changed_files`, `BLOCKED` without a blocker, or a test entry without an
exit code is rejected/warned as an unverified claim.

The orchestrator still verifies git, the diff, the changed files, the commit, the tests, the scope
and the real worktree state: `orch.py verify --id <id>` does that mechanically and records the
evidence (`verification`, `scope_validation`, `worktree_clean`, `changed_files`). A worker claim that
disagrees with git is not a tie.

## Role policies

Formalised in `contracts.ROLE_POLICIES` and applied as the default `mutation_policy` per role.

| Role | May | May not | Default write zone |
|---|---|---|---|
| orchestrator | plan, read metadata/git/diffs/reports, run and verify commands, coordinate, integrate approved work, persist state, manage Herdr | implement delegated work silently; take over a delegated task | state and run-owned resources |
| worker | read what the task needs, write inside `write_scope`, run the required checks, create its own focused commit on its branch | expand its own scope, touch files outside the contract, start another task, merge its own branch, touch another worker's worktree/branch/pane | `write_scope`, inside its own worktree |
| reviewer | read code and diff, run non-mutating checks, produce a VERDICT | edit code, commit, change the implementation | read-only |
| tester | run test plans, reproduce and diagnose, write only into authorised temp/build/cache dirs | change the implementation, commit product code | temp/build/cache only |
| fixer | change the original task branch inside the original scope, address the findings it was sent | refactor beyond the findings, touch other tasks' branches | original branch + scope |
| researcher | read, report structured findings | edit project files | read-only |

A FAIL verdict always goes back to the worker/fixer responsible for the work - not to the
orchestrator, and never fixed silently by the orchestrator.

## DIRECT mode and the delegated-task boundary

DIRECT mode still exists for genuinely trivial work, and the ordinary rules of the run (the three
configuration axes, scope, ownership) still apply to it.

Once a task has entered the orchestrated workflow and been dispatched to a worker, the orchestrator
must not silently implement it. Moving a delegated task to DIRECT - or forcing `ready`
without a valid contract - is an **explicit, recorded transition**:
`set-task --status ready --force --note "<why>"` logs a `task_direct_override` event and writes the
reason into `decisions.md`. Forcing an integration past the gate logs `merge_gate_bypassed` the same
way. Silent corrections destroy attribution; recorded ones are auditable.
