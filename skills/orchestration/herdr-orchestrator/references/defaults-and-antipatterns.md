# Recommended defaults and anti-patterns

## Default policy block

Adopt these unless the user or the repository says otherwise. Record any deviation in
`decisions.md` with the reason.

```yaml
run_config:
  coordination_mode: supervised_auto     # assisted | supervised_auto | auto
  team_mode: semi_auto                   # manual | semi_auto | auto
  worker_execution_mode: autonomous      # autonomous | interactive
  substitutable_kinds: false             # a kind the user pinned is never swapped silently
  escalate_on: [new_trust_decision, credentials, material_scope_change,
                ambiguous_recovery, out_of_scope_work, run_external_effects]

orchestration:
  prefer_delegation_for_complex_tasks: true
  prefer_parallel_when_independent: true
  max_parallel_workers: auto          # bounded by independence, pane size and provider limits

contracts:
  contract_before_dispatch: true      # no mutating task is delegated without a validated contract
  worker_may_edit_contract: false     # material changes go through the orchestrator (--force + reason)
  result_contract_required: true      # DONE | BLOCKED | FAILED | NEEDS_INPUT
  result_is_evidence: false           # a report is a claim; git + observed output are evidence

scope_enforcement:
  install_commit_gate_per_worktree: true   # orch.py guard --install-hook
  per_kind_write_boundary_when_verified: true   # orch.py guard --plan --verify-launch
  claim_prevention_without_verification: false  # unverified mechanism => prevention: none
  integrate_on_scope_fail: false

checkpoints:
  checkpoint_policy_default: auto     # auto | required | none (auto = long/complex tasks only)
  checkpoint_dir: .orchestrator/checkpoints
  commit_per_checkpoint: false        # commits are for coherent states, not for bookkeeping

watchdog:
  stall_after: 900                    # seconds without work activity before "potentially stalled"
  sample_interval: 120                # mechanical samples, never a tight loop
  kill_on_single_timeout: false       # a stall is an inspection prompt, not a kill order
  watchdog_decides: false             # observation only: no code, no merges, no prompt answers

git:
  worktree_per_mutating_task: true
  worker_commits_own_changes: true
  integration_strategy: merge-no-ff
  auto_resolve_conflicts: false

merge_gate:
  required: true
  ready_false_means: do_not_merge
  bypass_requires: explicit_force_plus_recorded_reason

review:
  independent_reviewer: true
  reviewer_read_only: true
  review_uses_the_same_contract: true
  structured_verdict: true
  require_pass_before_merge: true
  max_fix_cycles: 3

testing:
  task_local_tests_before_completion: true
  integration_tests_after_merge: true
  require_observed_output: true

recovery:
  persistent_state: true
  reconcile_runtime_on_start: true
  reconstruct_before_resume: true     # never "continue where the other one stopped"
  one_writer_per_worktree: true

safety:
  never_kill_unknown_agents: true
  never_close_unknown_panes: true
  never_guess_resource_ids: true
  stop_on_unapproved_blocked_prompt: true
  auto_trust_unknown_repositories: false
  auto_accept_new_hooks: false
  clean_only_owned_resources: true
```

## Anti-patterns

Never do these by default.

**Shared mutable checkout.**

```text
worker1 ---> same cwd <--- worker2
```

for independent concurrent coding. It produces interleaved edits, lost work and unreviewable diffs.
One worktree per writer - including during a replacement, where the old worker must be stopped before
the new one starts.

**Sequential fake parallelism.**

```text
prompt A --wait
prompt B --wait
```

when the tasks are independent. It turns a two-agent team into a two-agent queue and doubles elapsed
time. Submit everything, then monitor.

**Delegating a mutating task without a contract.** Free-form prompts cannot be validated, cannot be
diffed, cannot be handed to a reviewer and do not survive recovery. If the task writes files, it gets
a contract first, or it is not delegated.

**Accepting a change because it looks good.** That is not a gate field. Contract, scope, tests, review,
worktree and commit are: when they do not all pass, the branch is not eligible for integration.

**Treating the worker's result report as evidence.** `result: DONE` with a commit hash the worker
invented is a claim. Verify git, the diff, the commit and the observed test output.

**Widening the scope to fit the code.** If the diff left `write_scope`, the work goes back to the
worker (correct or revert). Adjusting the contract to match what arrived inverts the whole mechanism;
a genuine scope change is an escalation and a new contract revision with a recorded reason.

**Fixing a scope violation yourself.** The orchestrator records, identifies and returns; it never
repairs delegated work silently, and never bypasses its own commit gate.

**Claiming prevention that was not verified.** Only mechanisms verified on the host may be called
mechanical prevention. For everything else, say `prevention: none` and rely on detection - an
invented deny flag is a false guarantee.

**Killing a worker on a single timeout.** Working + process alive + recent output is healthy. Stall
detection uses combined signals, is conservative, and produces an inspection prompt - not a kill.

**Using the LLM as the poller.** The watchdog is the poller: mechanical, cheap, deterministic, logged.
The orchestrator's reasoning is for decisions, not for watching a pane.

**Letting the watchdog decide.** It observes, classifies and reports. Architecture, merges, scope
decisions and prompt answers stay with the orchestrator (and the user).

**Checkpointing (or committing) trivia.** Checkpoints are for long/complex tasks at meaningful
transitions, and commits are for coherent, reviewable states. Forty commits to have forty checkpoints
is noise, not resilience.

**Resuming with "continue where the other one stopped".** Without a reconstructed state (contract,
branch, commits, changed files, checkpoint, remaining work) that phrase hides unknown missing work.
Rebuild first, then dispatch.

**Reviewer edits code.** The reviewer must stay independent and read-only; a reviewer that fixes what
it reviews has reviewed nothing - and it must judge the contract the worker received, not a paraphrase.

**Orchestrator fixes everything.** Silently repairing delegated work destroys ownership, attribution
and the review boundary. Send findings back, or declare the task DIRECT up front - explicitly and
recorded.

**Trusting worker text.** "Tests pass" is a claim. Inspect artifacts, diffs, commits and command
output.

**Guessing pane, workspace or agent IDs.** They are opaque and server-scoped. Parse responses.

**Deleting resources without checking ownership.** Cleanup touches only what this run recorded as
owned, and only after integration is verified.

**Auto-approving blocked prompts.** `blocked` means a person is being asked to decide about trust,
hooks, credentials, privilege or destruction. Inspect, classify, ask.

**Parallelizing by habit.** Spawning workers because agents are available ignores file overlap and
shared state. Parallelism is a property of the tasks, not of the tooling.

**Letting the plan live in context only.** A plan that exists only in the conversation cannot be
recovered after a restart. Persist as you go.

**Merging unreviewed work.** Mutating output normally passes verification, tests and independent
review before integration. Only a trivial task or explicit user authorization is an exception.

**Inventing autonomy flags.** A fabricated `--yolo` / `--skip-permissions` either fails or silently
leaves the worker interactive. Discover the invocation from the installed binary, then verify the
observed argv.

**Confusing the axes.** Reading "use only X" as licence for unattended coordination, or "coordinate it
yourself" as licence to replace a pinned kind. One axis per instruction.

**Autonomy as a scope bypass.** Autonomy removes prompts, not limits: no credentials, no other
projects, no run-external resources, no unrequested publishes.

**Editing this skill mid-run.** Lessons become proposals (`.orchestrator/skill-proposals.md`), never
silent edits to a skill that is currently steering the work.

## Philosophy

A good orchestrator does not maximize the number of agents. It maximizes correctness, useful
concurrency, isolation, recoverability, observability, clear ownership, independent verification and
safe integration. The question is not "how many agents can I spawn?" but "what execution graph
minimizes risk and elapsed time while keeping every change attributable, reviewable and
recoverable?"

Deterministic enforcement beats good intentions: guards limit, gates decide, the watchdog observes,
the reviewer judges, and the orchestrator coordinates instead of implementing.
