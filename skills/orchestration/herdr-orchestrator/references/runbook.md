# Runbook: the sequence I actually run

Dense, in order, copy-pasteable. Every command here was executed on a live run (2026-09-17, two
workers + reviewer + merge train, plus a kill-9 recovery drill). Where order matters, it says so —
those are the mistakes that cost me runs.

## 0. Bootstrap (never skip)

```bash
test "${HERDR_ENV:-}" = 1 && echo inside || echo outside   # refuse to drive a session from outside
timeout 20 herdr status                                    # client vs server version
herdr agent list; herdr workspace list                     # what is already alive (the user's too)
git -C <repo> status --short --branch; git -C <repo> rev-parse HEAD
python3 scripts/orch.py --repo-root <repo> init --run-id <run>       # or `reconcile` if state exists
```

## 1. Plan, contracts, and the overlap gate BEFORE anything else

```bash
O=scripts/orch.py                      # run from the skill dir or use the absolute path
python3 $O --repo-root <repo> add-task --id <t> --title '...' --scope 'src/x.py' --acceptance '...'
python3 $O --repo-root <repo> contract --id <t> --role worker --objective '...' \
  --write-scope 'src/x.py' --forbidden-scope 'tests/**' --acceptance '...' \
  --required-check 'python3 -m unittest tests.test_x -v' \
  --base-commit "$(git -C <repo> rev-parse HEAD)" \
  --model '<pinned model>' --budget-tokens 60000
python3 $O --repo-root <repo> overlap; echo "exit=$?"     # exit 2 = a collision; DO NOT dispatch
```

- `overlap` refuses two live writers whose write scopes can meet. Serialise or re-slice; that is
  cheaper than any merge.
- One deliverable per task. A task whose `write_scope` is a bare file is fine (`src/x.py` now matches
  both readings) — but a bare `src` catches everything below it.
- **Run the required check against the base commit before you dispatch.** A check that cannot pass —
  contradictory assertions, a missing `tests/__init__.py` (unittest discovery skips the directory), a
  wrong cwd — burns the worker and makes the gate refuse honest work. A drill shipped a task whose two
  tests asserted opposite things; the worker noticed, implemented it correctly anyway, and the gate
  refused because the check was impossible.
- Record the **model** and a **budget** on every task; they are part of the contract.

## 2. Isolate, record, THEN guard (this order is load-bearing)

```bash
OUT=$(herdr worktree create --cwd <repo> --branch agent/<run>/<t> --base <sha> \
      --path <repo>/.orchestrator/worktrees/<run>/<t> --label <t> --no-focus)
PANE=$(printf '%s' "$OUT" | python3 -c 'import json,sys;print(json.load(sys.stdin)["result"]["root_pane"]["pane_id"])')
python3 $O --repo-root <repo> set-task --id <t> --worktree <wt> --branch agent/<run>/<t> --pane $PANE
python3 $O --repo-root <repo> guard --id <t> --install-hook --kind opencode --plan --verify-launch
```

- **Pass the plan's `launch_args` at dispatch**, and read what level the plan claims before
  trusting it: `mechanical` only for a kind with a launch-time probe (`opencode`), `configured` for a
  parsed-but-unexercised boundary (`claude`), `coarse` for worktree-level sandboxes (`codex` — and its
  sandbox includes /tmp, so keep worktrees out of /tmp), `none` where no boundary exists (`prime`; use
  its `--autonomous-gate` and token limits instead).
- **Record the worktree before installing the guard.** Installing first used to fall back to the
  shared checkout and still log `scope_guard_installed`.
- Pass **`--kind`** explicitly, or record the launch first: a bare `auto` means no adapter is looked
  for and the plan says `prevention: none`.
- Read the output: `hook.installed: true` **and** `hook.worktree_config_file` pointing at *this*
  worktree's gitdir, and `launch_verification.verified: true` with `reasons: []`. Anything else means
  the worker runs with detection only — say so out loud instead of assuming prevention.
- For opencode 1.18.31 the verified mechanism is the generated file exported as
  `<worktree>/.opencode/opencode.json` (edit + bash deny-by-default, checkpoint directory allowed).
  Do NOT export `OPENCODE_CONFIG` at it from outside the project: measured, that breaks the matching
  of relative `edit` patterns and refuses even the scoped file. `OPENCODE_PERMISSION` and
  `OPENCODE_CONFIG_CONTENT` are inert.

**Give every worker its own workspace.** Never split a worker beside the user's pane: they read and
type there. `herdr pane move <pane> --new-workspace --label <task> --no-focus` (or
`herdr workspace create --label <task> --cwd <worktree>`); the user's workspace must end up holding
only their own pane. `pane move --tab` needs `--split` + a target pane — `--new-workspace` is the
form that never lands in someone's view.

## 3. Dispatch (no `--wait`; target by pane)

```bash
herdr agent start w-<t> --kind opencode --pane $PANE --timeout 120000
python3 $O --repo-root <repo> set-task --id <t> --status working --agent w-<t> \
  --launch-mode autonomous --launch-kind opencode --launch-verified 1
herdr agent prompt $PANE "<contract rendered + steps + the result-report format>"
```

- **Address agents by pane id.** Two opencode agents both end up named `opencode` in
  `herdr agent list`; a name is not a target when it is not unique.
- The prompt carries the contract verbatim: objective, `write_scope`, `forbidden_scope`, the
  `required_checks` command, and the report shape (`result: DONE|BLOCKED|FAILED|NEEDS_INPUT`,
  `commit`, `changed_files`, `tests` with exit codes).
- **Seed the checkpoint yourself** as soon as the worktree exists; never leave a running task with no
  checkpoint on disk. A worker that ignores the instruction (or is refused by a rule you got wrong)
  otherwise leaves a replacement reconstructing from Git alone — two live drills did exactly that:
  ```bash
  python3 $O --repo-root <repo> checkpoint --id <t> --set --worker w-<t> --phase 0 --total-phases 0 \
    --current 'dispatched; no artifact yet' --remaining "$(python3 $O --repo-root <repo> \
      contract --id <t> --show | awk '/acceptance_criteria/{getline; gsub(/^ *- */,""); print}')" \
    --commit "$(git -C <wt> rev-parse HEAD)"
  ```
  Tell the worker to update **`<worktree>/.checkpoint.json`** (a relative path inside its own
  worktree — allowed by the same config, excluded from git status); the orchestrator reads the newest
  of that file and the seeded copy. The watchdog flags `checkpoint_missing` when neither is updated
  (`checkpoint_after`, default 600s).
- Dispatch the whole wave before waiting on any of it.

**The boundary travels in the project config — export nothing.** The mechanism is
`<worktree>/.opencode/opencode.json`, written by `guard --plan`, read by opencode from the worker's
own cwd. Measured the hard way: `OPENCODE_CONFIG` pointing at a file **outside** the project makes
opencode stop matching the relative `edit` patterns, so the scope allow never lands and even in-scope
writes are refused (three live variants, all denied). So: no env var, no `pane run` export, no
wrapper. Prove it with the probe, which runs `opencode debug config` in the worktree with the env
unset:

```bash
python3 $O --repo-root <repo> guard --id <t> --plan --verify-launch --cwd <wt>   # verified: true
git -C <wt> status --porcelain          # must be empty: the config is in the worktree's exclude
```

## 4. Monitor mechanically

```bash
python3 scripts/watchdog.py --repo-root <repo> --json     # classifications, not opinions
herdr agent list
```

Act on the classification: `agent_gone`/`process_dead` → recovery; `blocked` → inspect the UI, never
auto-approve; `spinning` → narrow the contract. Never poll by hand-reasoning over pane text.

## 5. Verify yourself (the report is not evidence)

```bash
git -C <wt> log --oneline <base>..HEAD; git -C <wt> diff --name-only <base>..HEAD
git -C <wt> status --porcelain                                        # generated output does not count
(cd <wt> && eval "<the contract's required check>"); echo "exit=$?"
python3 $O --repo-root <repo> verify --id <t>                          # records commit + scope
python3 $O --repo-root <repo> result --id <t> --text "<worker's report>"
python3 $O --repo-root <repo> set-task --id <t> --tests-status pass --tests-command '<cmd>' \
  --tests-evidence <file>
```

## 6. Review independent, read-only, and expect the screen to eat it

```bash
RV=$(herdr pane split --current --direction down --cwd <repo> --no-focus \
     | python3 -c 'import json,sys;print(json.load(sys.stdin)["result"]["pane"]["pane_id"])')
herdr agent start reviewer --kind opencode --pane $RV --timeout 120000
python3 $O --repo-root <repo> review-package --id <t> --live > /tmp/pkg-<t>.txt
herdr agent prompt $RV "READ-ONLY. Review /tmp/pkg-<t>.txt ... reply task_id / VERDICT / findings"
```

- Pair the reviewer with a **different model or kind** than the producer when one is available; with
  one kind installed, a separate instance is the floor, and you say so in the report.
- A TUI reviewer's answer can leave the alternate screen (host scrollback never gets it). The
  fallback that works: *"escreva a revisão em /tmp/review.md e responda só o caminho"* — then read the
  file. Ask for `file:line` in the findings.
- Record the verdict: `set-task --id <t> --verdict PASS|FAIL` (FAIL → back to the worker, bounded).

## 7. Gate, then integrate the COMBINATION

```bash
python3 $O --repo-root <repo> merge-gate --id <t> --live      # every field must be pass/ready: true
git -C <repo> merge --no-ff agent/<run>/<t> -m "merge: <t>"
(cd <repo> && <the run-level check>)                          # re-run on the TRUNK after each merge
python3 $O --repo-root <repo> set-task --id <t> --status integrated --commit <sha>
```

A green branch proves nothing about the trunk it lands in. In the live run the trunk suite failed
after the first of two merges and only passed when both were in.

## 8. Recovery after a worker dies (verified drill)

```bash
PID=$(for p in $(pgrep -f '^opencode$|/opencode'); do \
      [ "$(readlink -f /proc/$p/cwd 2>/dev/null)" = "<wt>" ] && echo $p; done | head -1)
kill -9 "$PID"
python3 scripts/watchdog.py --repo-root <repo> --json      # -> agent_gone
python3 $O --repo-root <repo> resume --id <t>              # worktree/branch/commits/remaining criteria
python3 $O --repo-root <repo> replace-worker --id <t> --agent <new> --old-agent <old> --reason '...'
```

`replace-worker` prints the package you hand to the new worker: contract, branch, commits, changed
files, scope status and the latest checkpoint. Never send "continue where the other one stopped";
send that package.

Two mechanical details that only a live drill teaches:

- After a kill, the dead worker's pane can keep the agent REGISTERED, and `replace-worker` refuses
  ("still live — two writers in one worktree corrupt each other"). Close that pane
  (`herdr pane close <pane>`) before handing the worktree to the replacement; give the replacement a
  fresh pane (`herdr pane split`) — the old pane's agent prompt target is gone. The refusal itself is
  correct and worth trusting: it is what stops two writers from sharing one worktree.
- `checkpoint --set` is what writes; without it the command reads. Seed it at dispatch, update it
  when you take over a task, and treat the copy in the package as a claim to re-check, not truth. Checkpoints (`checkpoint_policy: required` for long tasks) are what make the
package complete — a worker killed before its first checkpoint forces reconstruction from Git alone,
and the package says exactly that.

## 9. Clean up, then keep the numbers

```bash
herdr agent list; herdr workspace list                     # close only what this run created
git -C <repo> worktree remove --force <wt>                 # after integration is verified
python3 $O --repo-root <repo> status; python3 $O --repo-root <repo> propose --kind <...> ...
```

Report at least: tasks dispatched/merged, tokens or context per worker (the CLI's own footer),
dispatches per accepted task, review-fail rate, replacements, and cost per accepted change. Lessons go
to `skill-proposals.md` via `propose` — never edit this skill mid-run.

## The four mistakes that cost me the most time

1. Installing the guard before recording the worktree (silent false prevention).
2. Dispatching on an `auto` kind (no adapter looked up, `prevention: none` misread as "no mechanism
   exists" instead of "you did not ask").
3. Trusting a per-branch green instead of re-running on the trunk.
4. Reading a worker's pane transcript instead of `git log`/`git diff` in its worktree.
