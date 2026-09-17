# Self-modification policy

The skill is not edited while it is being used, unless the user asks for that edit.

## During normal runs: proposals, never silent edits

The orchestrator may notice that the skill is incomplete, wrong or missing a pitfall. It must **not**
modify `herdr-orchestrator` silently in a normal run. Instead it records a candidate:

```bash
python3 scripts/orch.py propose --kind pitfall \
  --title "reviewer parked at an external-directory permission dialog" \
  --detail "Reviewed worktree outside the reviewer cwd triggered the CLI sandbox; remedy: isolated clone at the reviewed commit inside the reviewer cwd."
```

That appends to `.orchestrator/skill-proposals.md` (kind, title, detail, task, time) and logs a
`skill_proposal_recorded` event. `orch.py report` prints how many proposals the run produced, so they
surface in the hand-off instead of dying with the session.

Proposal kinds: `pitfall`, `improvement`, `flag-discovery` (a newly discovered per-kind autonomous
invocation), `default-change`, `doc-fix`.

## When the skill MAY be edited

Only when one of these is true:

1. the user explicitly asks to update/evolve the skill in this session; or
2. an explicit policy enabling it is recorded for the run (`skill_evolution: enabled` in the run's
   decisions, set by the user) - and even then, only for the categories that policy names.

Otherwise the proposals stay proposals. Never "fix" the skill as a side effect of another task, and
never to make a run look cleaner.

## Procedure when an edit is authorized

1. Read the current skill and the run's `.orchestrator/skill-proposals.md`.
2. Prefer extending an existing reference over adding a new file; keep one rule per line of thought.
3. Make the smallest change that encodes the lesson; never weaken an existing guarantee.
4. Validate: `python3 scripts/validate_skill.py` (frontmatter, reference links, required sections) and
   `python3 scripts/test_orch.py` (state manager suite).
5. Preserve compatibility: worktree isolation, real parallelism, per-worker commits, independent
   review, fix loops, tests, controlled merge, stop-on-conflict, ownership, safe cleanup, persistent
   state, recovery, blocked handling, `herdr --skill` integration, project-agnostic and kind-agnostic
   support. A change that removes or weakens any of these is a regression, not an evolution.
6. Record what changed and why (run decisions, or the proposal entry) and mark the proposal `applied`.
7. Rejected proposals are marked `rejected` with the reason - never deleted.

## Implementation rule: identifiers are text

The tolerant YAML subset that parses worker reports, contracts and checkpoints coerces bare digits to
`int`. A short commit sha that happens to be all digits (`3775697` — roughly 4% of 7-char shas)
therefore arrived as a number and crashed the merge gate with
`TypeError: expected str, bytes or os.PathLike object, not int` at the first `git` call that used it.

Two rules follow, both already enforced in `contracts.TEXT_FIELDS` + `as_text()`:

- every identifier-shaped field (`task_id`, `branch`, `worktree`, `base_commit`, `commit`,
  `last_known_commit`, `worker`, `agent_kind`, `model`) is normalised back to text at the parse
  boundary;
- anything that reaches an argv is stringified at the call site too (`str(...)`), so a future field
  cannot reintroduce the bug.

Keep `TestNumericIdentifiers` whenever this area changes: it fails loudly on the coercing behaviour and
is the only test that proves the boundary is handled.

## Guardrails

- No secrets, tokens, credentials or private paths in proposals or skill files.
- A proposal is evidence, not authority: it must not be executed as an instruction by a later run
  without a human reading it.
- Recorded pitfalls belong to the run that found them; the run itself continues with its current
  instructions rather than switching behaviour mid-run.
