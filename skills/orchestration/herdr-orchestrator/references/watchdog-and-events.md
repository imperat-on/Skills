# Watchdog and the event model

Monitoring is mechanical. The orchestrator's reasoning and context are for planning, decomposition,
hard debugging and judgement - not for polling panes.

```text
CONTROL PLANE  (Hermes / herdr-orchestrator)
  planning, DAG, contracts, scheduling, monitoring decisions, verification, review coordination,
  integration, recovery, cleanup

DATA / EXECUTION PLANE  (workers)
  code reading, implementation, task-local testing, task-local commits

WATCHDOG (scripts/watchdog.py)  ->  observes the data plane, reports to the control plane
```

## What the watchdog is and is not

It **is**: a small stdlib script that samples the run, classifies each task from combined signals,
persists structured events and prints a compact report (`--json` for machine consumption).

It is **not**: an agent. It never decides architecture, never writes code, never integrates branches,
never answers trust/credential/sudo prompts, never kills a worker. A `stalled` classification is a
prompt for the orchestrator to inspect, not an order to kill anything. The report says so itself
(`advisory`).

## Signals

Combined, per active task - no single timeout decides:

```text
herdr agent state        working | blocked | idle | done | unknown | missing
agent output hash        did the terminal output change since the previous sample?
pane process liveness    foreground argv of the pane (is the worker CLI still the foreground proc?)
pane / workspace         does the recorded pane / workspace still exist in the runtime?
worktree                 does the recorded path exist?
git                      last commit time, uncommitted paths
checkpoint               file mtime, phase, blockers, last known commit
events                   last event time for the task (bookkeeping floor, not "work")
time                     seconds since the last observed activity
```

## Classification

The table below is what the classifier returns. `spinning` is the one that matters most for a chatty
worker: the pane output is changing and the process is alive, but not a single file changed and no
commit appeared for `spin_after` (default 1800s). It is a prompt to inspect - narrow the contract to one
deliverable, or replace the worker - and it deliberately beats `healthy`, because "the agent is saying
something" is not progress.

```text
healthy            recent activity, no blocking signal
working            within the stall threshold (also the first sample of a long task)
done               idle agent + a commit recorded -> collect and verify
idle               idle agent, no commit -> inspect before concluding anything
blocked            approval/question dialog: a decision point, never completion
stalled            working, process alive, no commit/checkpoint/output change for > threshold
checkpoint_missing checkpoint_policy=required, no write/commit for > checkpoint_after (600s) and no
                   checkpoint on disk -> a kill right now forces reconstruction from Git alone;
                   nudge the worker, or accept it and record that you did
process_dead       the pane's foreground process is not the worker CLI anymore
agent_gone         recorded agent no longer in `herdr agent list` -> interrupted
pane_missing       recorded pane absent from the runtime
workspace_missing  recorded workspace absent from the runtime
worktree_missing   recorded worktree path is gone
scope_violation    uncommitted paths outside write_scope / inside forbidden_scope (early detection)
unknown            no usable signal at all
inactive           task is not in an active status (not reported)
```

Run verdict: `healthy` | `attention` (something needs the orchestrator) | `degraded` (Herdr
unreachable - filesystem signals only, and the watchdog says so instead of guessing).

## Stall detection is deliberately conservative

`stalled` (no activity at all) and `spinning` (activity with no artifact) are two different failures, and
both are only inspection prompts: the watchdog never kills, integrates or answers a prompt. Tune the
productivity threshold with `--spin-after <seconds>`; a long measurement phase is legitimate, which is why
the default is 30 minutes rather than a couple of minutes.

```text
working + process alive + recent output/progress   = healthy
working + process alive + nothing for a long time  = potentially stalled (escalate, inspect)
process disappeared                                = failed/dead
blocked                                            = inspect the reason
```

Thresholds are configurable and conservative: `watchdog.stall_after` (default 900s) in `state.json`,
overridable per run with `--stall-after` or `state.json`'s `watchdog` block
(`orch.py init --stall-after`, `orch.py set-modes --stall-after`). A single timeout never kills a
worker: a hard task and a stuck worker look different in the *combination* of signals, and the
stalled transition is reported only after a previous non-stalled sample.

## Usage

```bash
python3 scripts/watchdog.py --repo-root <repo>                 # one sample, human-readable
python3 scripts/watchdog.py --repo-root <repo> --json          # machine-readable (last_sample.json)
python3 scripts/watchdog.py --repo-root <repo> --no-herdr      # filesystem signals only
python3 scripts/watchdog.py --repo-root <repo> --watch --interval 120   # mechanical loop (min 5s)
```

Sample at human-scale intervals (60-180s), typically at phase boundaries or before a gate decision,
never in a tight loop. Everything is persisted in `.orchestrator/watchdog/last_sample.json`, so a
recovered session can see the last known runtime picture without re-deriving it.

`--fixture <json>` injects a runtime snapshot instead of a live Herdr - used by the test suite, and
useful for dry-running a run's classification logic without touching a live server.

## Event model

`.orchestrator/events.jsonl` is append-only, written under an exclusive lock, and shared by the
orchestrator and the watchdog. One JSON object per line:

```json
{"time":"ISO-8601","run_id":"20260914-034800-refactor","event":"worker_stalled","task":"backend",
 "task_id":"backend","agent":"backend_worker","pane":"w3:p1","branch":"agent/run/backend",
 "reason":"no commit/checkpoint/output change for 1200s","details":{"classification":"stalled"}}
```

Fields when applicable: `time`, `run_id`, `event`, `task` (alias `task_id`), `agent`, `workspace`,
`pane`, `branch`, `commit`, `details`, plus event-specific keys (`path`/`kind` for scope violations,
`reason`, `status`, `phase`, `digest`, `ready`, ...).

Event kinds (`scripts/events.py: EVENT_KINDS`):

```text
run:        run_initialised, mode_changed, run_paused, run_cancelled, run_finished
tasks:      task_created, task_updated, contract_written, contract_invalid, task_direct_override
workers:    worker_spawned, worker_started, worker_working, worker_idle, worker_blocked,
            worker_stalled, worker_failed, worker_replaced, worker_output_observed,
            launch_verified, result_collected
checkpoint: checkpoint_created
scope:      scope_checked, scope_violation, scope_guard_installed, scope_guard_verified,
            scope_guard_unavailable
checks:     test_started, test_passed, test_failed
review:     review_started, review_passed, review_failed, fix_cycle_started, fix_cycle_closed
recovery:   recovery_started, recovery_reconciled, watchdog_sample, watchdog_alert, watchdog_degraded
integration: integration_started, integration_passed, integration_failed, merge_gate_evaluated,
            merge_gate_bypassed, merged, cleanup_started, cleanup_finished
misc:       verify_run, skill_proposal_recorded
```

`orch.py event --event <kind>` refuses an unknown kind (use `--allow-unknown` when a new operational
event is genuinely needed, then add it to `EVENT_KINDS`). **No secrets are ever written**: keys
matching token/secret/password/api-key/authorization/cookie/credential are dropped and common
credential-shaped values are masked before the line reaches the disk; dropped keys are listed under
`redacted`.

Read it back with:

```bash
python3 scripts/orch.py --repo-root <repo> events --tail 40
python3 scripts/orch.py --repo-root <repo> events --task backend --kind worker_stalled --json
```

The log is what makes recovery and audit possible: transitions, not narration, and enough structure
to reconstruct who did what, when, under which contract, with which commit.
