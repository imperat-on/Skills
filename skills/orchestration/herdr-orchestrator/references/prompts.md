# Prompt templates

Structured, scope-bounded prompts. Fill every placeholder; delete brackets. Keep prompts short —
no worker receives the whole conversation, only its slice. All prompts are sent with
`herdr agent prompt <target> "<text>"`, without `--wait` when dispatching in parallel.

## Delegation (implementation worker)

One dispatch, one deliverable. A contract carrying several independent fixes is sent as slices: each
slice names a single objective, its own acceptance criterion and its own commit, and the next slice is
dispatched only after the previous one is verified. The template below is used per slice - not once for
a three-bug task, which is how a worker ends up reading for 40 minutes and writing nothing.

The prompt carries the **rendered contract** plus the operating rules. Generate the contract block with
`orch.py contract --id <task>` (or `contract --id <task> --show`) and paste it verbatim - never
paraphrase it, the worker and the reviewer must judge the same object.

```text
You are worker <agent-name>. You implement; the orchestrator coordinates. You own this task only.

TASK CONTRACT (do not edit it, do not reinterpret it):
<rendered contract: task_id, role, objective, write_scope, read_scope, forbidden_scope,
 acceptance_criteria, required_checks, deliverables, branch, worktree, base_commit,
 mutation_policy, when_blocked>

Working directory:
<absolute worktree path>            (branch <branch>, base <base-commit>)

Rules:
- write only inside write_scope; never touch forbidden_scope;
- a scope guard refuses commits with out-of-scope paths - if it fires, revert the offending path
  and report, never widen the scope and never use --no-verify;
- do not take another task, do not merge your branch, do not touch another worker's worktree;
- run the required checks before reporting;
- commit your own focused commit on this branch (message: <message>);
- when blocked: report the reason. Do not answer trust/credential/sudo prompts. Do not expand scope.

Checkpoints (<required | whenever you finish a phase | not needed>):
- record progress with: python3 <skill>/scripts/orch.py --repo-root <repo> checkpoint --id <task>
  --set --phase <n> --total-phases <N> --completed "<...>" --current "<...>" --remaining "<...>"
  [--commit <sha>] [--decision "<...>"]
- checkpoint at meaningful transitions, not on a timer; do not create commits only to checkpoint.

Before completing:
- inspect your own diff; ensure `git status` contains only intended changes.

Return the result contract, in exactly this shape:
result: DONE | BLOCKED | FAILED | NEEDS_INPUT
task_id:
commit:
changed_files: []
tests:
  - command:
    exit_code:
    result:
scope_violations: []
blockers: []
notes: []
```

## Research (read-only)

```text
You are researcher <agent-name>. Do not modify any file. Working directory: <path>.

Question:
<what must be established>

Investigate:
<areas/files/commands to inspect>

Return:
FINDINGS:            (facts with file paths and line references)
ARCHITECTURE NOTES:  (how the relevant parts fit together)
RISKS / UNKNOWNS:
RECOMMENDED NEXT TASKS:  (in priority order, with rationale)
```

## Review (independent, read-only)

Build the reviewer's input mechanically rather than by hand:

```bash
python3 scripts/orch.py --repo-root <repo> review-package --id <task> --live \
  > .orchestrator/reports/<task>-review-prompt.txt
```

That already contains the original contract, base commit, worker commit/branch, changed files, scope
validation, acceptance criteria, required checks, the recorded test evidence, the read-only
instruction and the verdict shape. Send it as the prompt (prefix with the agent identity line) and
never replace it with a paraphrase - the reviewer must judge the same contract the worker received.

```text
You are reviewer <agent-name>. You are READ-ONLY: do not edit, format, commit or fix anything.

<review-package content: contract, base/commit/branch, changed files, scope validation,
 acceptance criteria, required checks, test evidence>

Inspect the diff, the commit, the tests and the surrounding architecture yourself.
Do not take the worker's summary as evidence.

Return, in exactly this shape:
verdict: PASS | FAIL
blocking_findings: []      (actionable, referenced to file/behaviour; required when FAIL)
non_blocking_notes: []
scope_findings: []
acceptance:
  <criterion>: PASS | FAIL
```

A FAIL verdict with no actionable findings is not usable - ask for specifics rather than relaying a
vague verdict. Record the verdict on the task (`set-task --id <task> --verdict PASS|FAIL`); that value
is what the merge gate reads.

## Fix cycle (findings back to the author)

```text
You are worker <agent-name>, continuing task <task-id> in the same worktree and branch
(<worktree path>, <branch>). The original contract still applies and has not changed.

Independent review returned FAIL. Fix exactly the following findings:
<numbered findings, each with file/behaviour reference; include the reviewer's scope_findings>

Constraints:
- stay inside the original write_scope (<write_scope>) and out of forbidden_scope (<forbidden_scope>);
- add commits on this branch; do not amend or rewrite existing history unless explicitly told to;
- re-run: <required checks>

Return the result contract again, plus for each finding: what changed and the evidence it is fixed.
```

## Checkpoint nudge (to a running worker on a long task)

```text
Checkpoint your progress before you continue:
python3 <skill>/scripts/orch.py --repo-root <repo> checkpoint --id <task> --set \
  --phase <n> --total-phases <N> \
  --completed "<...>" --current "<...>" --remaining "<...>" [--commit <sha>] \
  [--decision "<...>"] [--blocker "<...>"]

Report anything that changed the plan. Do not create a commit only to checkpoint: commit when the
work is in a coherent, reviewable state.
```

## Worker replacement (same task, after a failure)

Generated mechanically, so the new worker receives verified state instead of a promise:

```bash
python3 scripts/orch.py --repo-root <repo> replace-worker --id <task> --agent <new-agent> \
  --old-agent <old-agent> --reason "<provider 503 | pane disappeared | stalled | ...>"
```

The command refuses while the previous agent still looks live, records `worker_history` and
`replacement_count`, re-derives git reality, and prints (and writes to
`.orchestrator/reports/<task>-replacement-N.txt`) a package containing: the unchanged contract, the
worktree/branch/base, the commits since base, the recorded commit and whether it exists, the changed
files, the scope status, the latest checkpoint, the remaining work, existing findings/verdict and the
one-writer-per-worktree rule. Send that package as the prompt:

```text
You are worker <new-agent-name>, replacing a worker that failed on task <task-id>.
Work in the SAME worktree and branch, so existing work is preserved.

<replacement package: contract, current worktree/branch/base, verified commits/diff, scope status,
 latest checkpoint, remaining work, findings, failure reason>

Do not redo completed work. Verify what is already there yourself, finish the remainder, stay inside
write_scope, run the required checks, commit, and return the result contract.
```

Never replace "the state" with the phrase "continue where the other one stopped": the package exists
precisely because that phrase hides unknown missing work. Do not create a second branch unless it is
genuinely necessary.

## Recovery / resume (after session loss)

```text
You are worker <agent-name>, resuming task <task-id> after an interruption.

Working directory: <worktree path>   branch <branch>   base <base-commit>

Task contract (unchanged):
<rendered contract>

Reconstructed state (from git + checkpoint + orchestrator state, not from memory):
<git log --oneline base..branch, git status --short, changed files, scope status, latest checkpoint>

First, inspect the worktree and state what is already done. Then finish the remaining work, run the
required checks, commit, and return the result contract.
```

## Blocked-prompt investigation (to the user, not to the agent)

```text
Agent <name> on task <id> is blocked. Herdr reports: <state/output excerpt>.
Classified as: <category>.
Proposed action: <exact keystrokes/decision you would make>.
Waiting for confirmation because this touches <trust/hooks/credentials/destructive/production>.
```

Never answer a blocked approval dialog on your own authority. Report the classification and the
exact action, and wait.

## Checkpoint approval request (`coordination_mode: assisted`)

```text
Checkpoint: <team creation | start of execution | integration | cleanup>
Mode: assisted (approval required before proceeding)

Plan:
<the exact next actions, with IDs/paths/branches/commits>

Acceptance criteria:
<measurable criteria per task>

Resources this will create:
<agents, worktrees, branches, panes - all owned by this run>

Risks:
<what could go wrong, and what I will do then>

Reply to approve, adjust, or stop.
```

Read-only preparation is already done, so approving costs one message and no re-planning.

## Progress update (`supervised_auto`, and phase boundaries in `auto`)

```text
<n>/<total> tasks | phase: <planning|dispatch|working|review|integration|validation|cleanup>

agent      | task     | state    | branch/commit
<one row per active task>

blocked:   <none | agent X, classified reason>
decisions: <mode changes, scope notes, deviations>
notable:   <only what changes the plan or the user's expectations>
```

Keep it to one screen; a checkpoint is not a transcript. In `auto`, send it at phase boundaries and at
the end, not per transition.
