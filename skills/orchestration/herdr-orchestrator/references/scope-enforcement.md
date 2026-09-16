# Scope enforcement: prevention and detection

A worker gets an explicitly limited `write_scope`. Two independent layers keep it there:

```text
Layer A - PREVENTION   mechanical, where the harness genuinely supports it
Layer B - DETECTION    always on: compare the real diff against the contract
```

Layer B alone is not enough: a change that "looks good" must never be accepted just because it looks
good. Layer A alone is not enough either: prevention is only as good as the harness, and every
mechanism below has a documented boundary.

## Layer A - what is mechanically enforceable today

A mechanism is Layer A only once it is proven IN FORCE against the installed binary version. The opencode
adapter is the cautionary case: 1.18.30 rejects the generated `permission.edit` shape at startup
(`Expected PermissionActionConfig`), so the exported environment does not restrict the worker - it stops
the worker from starting, and the run burns time on what looks like a permission problem. When the
adapter reports the environment as rejected, `guard --plan` emits `prevention: none` with the reason and
the run falls back to the commit gate plus `validate-scope`. Re-verify the mechanism whenever the CLI
version changes.

Every mechanism below was verified on this host before being claimed. Nothing else is implied; for a
kind without a verified mechanism the honest answer is `prevention: none`.

| Mechanism | Boundary | Evidence | Bypass |
|---|---|---|---|
| `git config --worktree core.hooksPath` + a run-owned `pre-commit` gate | every commit in the worktree: a staged path outside `write_scope` / inside `forbidden_scope` refuses the commit | git 2.55.0: the linked worktree's commit is refused, the shared checkout's hooks path is untouched | `git commit --no-verify` (then Layer B catches it) |
| `OPENCODE_PERMISSION` (or `OPENCODE_CONFIG_CONTENT`) with `edit` deny-by-default + `write_scope` allows + `external_directory` deny | the `edit` tool (edit/write/patch) at sub-path resolution, for opencode | opencode 1.18.30: `opencode debug config` reports the injected rules even when the project config says `edit: allow`. A plain `OPENCODE_CONFIG` **file** is overridden by the project config and is therefore never used alone | a shell command can still write files |
| `codex -s workspace-write` | coarse: writes confined to the worktree | codex-cli 0.154.0 (advertised flags) | no sub-path denial at all |
| claude `--settings` / `--permission-mode` | **not claimed**: deny-rule behaviour under `bypassPermissions` was not verified here | claude 2.1.263 exposes the flags only | treat as detection-only |
| any other kind | none | no verified mechanism | detection only |

### Installing and verifying the guards

```bash
# 1. commit gate, scoped to this worktree only (the shared checkout is left alone)
python3 scripts/orch.py --repo-root <repo> guard --id <task> --install-hook

# 2. per-kind prevention plan, generated from the contract
python3 scripts/orch.py --repo-root <repo> guard --id <task> --plan
#    -> .orchestrator/guards/<task>/{prevention-plan.json,opencode-permission.json,hooks/}

# 3. prove the prevention is in force BEFORE trusting the worker
python3 scripts/orch.py --repo-root <repo> guard --id <task> --verify-launch
#    opencode: runs `opencode debug config` under the intended environment and asserts the
#    effective rules deny by default and still allow the contracted scope
```

The launch environment must actually reach the worker process. Two verified-in-mechanism routes:

1. `herdr pane run <root-pane> "export OPENCODE_PERMISSION='<json>'"` **before**
   `herdr agent start`, then `herdr pane run <pane> 'echo "$OPENCODE_PERMISSION"'` to confirm the
   variable is set in that shell (the shell is still free - no agent has started);
2. fallback: start the worker as a wrapper command in the pane
   (`herdr pane run <pane> "OPENCODE_PERMISSION='<json>' opencode"`), then `herdr agent rename`.

Then capture the value the worker actually sees and hand it back:
`guard --id <task> --verify-launch --observed '<value>'`. `verify-launch` returns non-zero when the
effective rules do not match the contract, so the orchestrator cannot silently proceed with an
unverified launch. The `install-hook` path additionally writes a `contract.json` snapshot next to the
hook, so the gate never depends on mutable orchestration state.

## Layer B - detection (always)

```bash
python3 scripts/orch.py --repo-root <repo> validate-scope --id <task>
python3 scripts/orch.py --repo-root <repo> validate-scope --id <task> --json   # machine-readable
python3 scripts/scope_guard.py check --task-id <task> --repo <repo> --worktree <wt> --json
python3 scripts/scope_guard.py check --task-id <task> --repo <repo> --include-dirty   # + worktree
```

The comparison is `git diff --name-only <base>...<branch>` (plus uncommitted paths with
`--include-dirty`), classified deterministically against the contract:

```text
SCOPE: PASS
```

```text
SCOPE: FAIL

unexpected:
- infra/deploy.yml

forbidden:
- database/schema.sql
```

Rules:

- `unexpected` = a changed path outside `write_scope`; `forbidden` = a path matching
  `forbidden_scope` **even when it also matches `write_scope`** (forbidden wins);
- `.orchestrator/**` and `.git/**` are always ignored;
- directory entries are recursive (`src/ui` behaves like `src/ui/**`); `**` crosses path separators,
  `*` and `?` do not; the ignore rules are the contract's, not git's;
- exit code 1 (`FAIL`) means **the task may not be integrated**;
- the verdict is stored in `tasks.json.scope_validation` and is what the merge gate reads.

## Violation handling (the orchestrator's obligation)

1. record it - `scope_violation` events name every offending path, with `kind`;
2. identify the files and the responsible task;
3. send the task back to the worker that owns it (same worktree, same branch) and require a
   correction or a revert - never fix it yourself, never "adjust the scope" to match the code;
4. re-run verification + tests + review on the corrected commit;
5. if the scope genuinely must change, that is an escalation to the user and a new contract revision
   through `orch.py contract --force` with a recorded reason.

The watchdog additionally reports out-of-scope **uncommitted** paths at sample time, which is early
detection *before* the commit - the orchestrator can interrupt the worker instead of repairing the
history later.

## Honest boundary statement

Real mechanical prevention today: (a) the run-owned commit gate for every kind (commit boundary),
(b) sub-path write denial for `opencode` via its permission rules, (c) worktree confinement for
`codex`. Everything else is detection plus the commit gate. In particular:

- no mechanism prevents a worker from *writing* an out-of-scope file in the working tree when its
  kind has no verified write-boundary support - that is caught by Layer B and by the watchdog;
- a shell command inside opencode is not path-restricted by `permission.edit`;
- `--no-verify` defeats the commit gate; the violation is then detected deterministically, the merge
  gate refuses integration, and the bypass is recorded;
- `read_scope` is never enforced as a rule (it describes what the worker needs to read) and must not
  be presented to the user as a guarantee.

None of this is a licence to weaken the gate: `ready: false` still means do not merge.
