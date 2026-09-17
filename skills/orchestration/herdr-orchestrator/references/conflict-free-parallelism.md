# Conflict-free parallelism and integration at scale

How to run N writers on one repository without paying for it at merge time. Everything here is
about **authoring fewer collisions**, not resolving them faster. Sources are cited with the number
that justifies the rule.

## The economics that decide the shape

- **Fan-out is not free and is often negative.** Measured Claude Code fan-out vs sequential across
  three model families (Jul 2026): subagents used **2.6x-5.9x the input tokens** of doing the same
  work sequentially and were **not faster on any timed task**; one matched pair cost 513k input
  tokens vs 121k direct. Cache misses pushed price-weighted cost to ~5x.
  <https://systima.ai/blog/subagent-tax>
- **Multi-agent costs ~15x chat tokens** (agents alone ~4x), and token usage alone explained **80%**
  of performance variance in Anthropic's production data. Their own guidance: multi-agent fits
  breadth-first, high-value work, and "most coding tasks involve fewer truly parallelizable tasks
  than research". <https://www.anthropic.com/engineering/multi-agent-research-system>
- **Runaway fan-out is the single largest overspend failure mode.** Reported: one task quietly
  spawned 7 subagents that drained a 5-hour budget; a review step recruited 41 verifiers, later
  reports reached 102 and 415 agents. Cap breadth and depth; require a stated reason to exceed.
  <https://systima.ai/blog/subagent-tax>
- **Conflict base rates to budget for**: ~19.8% textual conflict among same-agent co-active work
  pairs vs **41.7% across different agent products**; ~84% of conflicts land in source files, ~42%
  structural (modify/delete, add/add). Build and semantic conflicts are not counted in those
  numbers. <https://www.agentpatterns.ai/workflows/concurrent-agent-pr-merge-conflicts/>

## Decomposition rules (cheapest fix, applied first)

Apply in order; stop at the first rung that removes the overlap.

1. **Gate dispatch on file scope, not on merge.** The contract already carries `write_scope`.
   Before dispatch, refuse any task whose `write_scope` intersects the `write_scope` of a live or
   about-to-be-dispatched task. A reference run of 194 tasks → 91 specs → 71 worktrees peaked at 35
   simultaneous worktrees with **zero merge conflicts** by rejecting overlapping specs at
   task-creation time. <https://withagents.dev/posts/post-06-parallel-worktrees>
2. **One owner per file.** For a file two tasks genuinely need: (a) designate one owner, (b) other
   writers send change requests to the owner, (c) the owner applies them sequentially, or (d)
   extract an interface/contract file the non-owner imports **read-only**. Ownership is assigned by
   directory, module or layer. Cardinal rule: one owner per file.
   <https://github.com/wshobson/agents/blob/main/plugins/agent-teams/skills/parallel-feature-development/SKILL.md>
3. **Contract-first decomposition.** Generate the interfaces between domains *before* splitting
   implementation, so each worker owns a distinct contract boundary and can build against APIs that
   do not exist yet. <https://github.com/painted-porch/marcus/blob/main/docs/source/concepts/contract-first-decomposition.md>
4. **Vertical slices beat horizontal layers.** "One agent per layer" (UI / service / data) funnels
   every writer into the same files and maximizes overlap; a vertical slice owns one end-to-end path
   through all layers. <https://deviq.com/architecture/vertical-slice-architecture/>
5. **Serialise only the genuinely fused work.** The coordination ladder is: partition by ownership →
   isolate + advisory reservations → serialise the high-overlap case. Blanket serialisation is the
   last rung, never the first.
6. **Advisory reservations for hot shared files** (manifests, migrations, route tables, barrel
   files): take an `flock`-style lock before editing; if it is not acquired quickly, **stop and
   report** instead of retrying. <https://dev.to/olivia_craft/claudemd-for-multi-agent-claude-code-11-rules-to-stop-your-agents-conflicting-48ac>
7. **When stale snapshots matter more than textual conflicts**, keep a single write lane: agents
   re-scan the repo while working, so a second concurrent writer makes every reader reason from a
   snapshot that stopped being true. Analysis and tests can still fan out; mutations go through one
   writer. <https://philliant.com/posts/20260810-one-agent-one-repo-for-writes/>
8. **Codeowners-style ownership as data** when the repository already has path ownership: make it
   machine-readable so the gate can ask "who must bless this path" instead of relying on memory.
   <https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners>
9. **Sparse-checkout worktrees** turn the partition into a mechanical boundary: the worker's
   worktree physically contains only its assigned directories. Detection stays on; prevention stops
   being contractual. <https://www.agentpatterns.ai/workflows/concurrent-agent-pr-merge-conflicts/>

## Parallel limits (how many writers are sane)

| Limit | Value | Source |
|---|---|---|
| Workers the orchestrator dispatches and absorbs status from | **2-4** | synthesis |
| Documented per-human sweet spot | 3-5 | worktrunk docs (5-10 supervised) |
| Where review overhead exceeds throughput gain | 5-7 | synthesis |
| Cap in a 194-task reference run | 8 (peaked at 35 live worktrees, thread-pooled) | withagents.dev |
| Hardware ceiling on a 16 GB workstation | ~2 CLI sessions before memory pressure (150-500 MB/session + MCP servers) | aq.dev |
| Branch lifetime | ≤ a couple of days; re-dispatch leftovers as a fresh short-lived branch | trunkbaseddevelopment.com |

Ports, databases, dev servers, `.env` files and caches must be **isolated per worktree** exactly
like files are — a shared port is a conflict that no scope check sees.
<https://aq.dev/guides/run-multiple-ai-coding-agents-in-parallel/>

## Integration: validate the combination

The rule that makes parallel work safe: **a branch that passes its own tests proves nothing about
the repository after it merges next to another branch.** Both can pass alone and break the trunk
together. So:

1. **Re-validate after every integration.** Sequence: gate a branch → merge → run the required
   checks **on the merged result** → only then dispatch or integrate the next. GitLab merge trains
   and bors exist precisely because merged-results pipelines are insufficient.
   <https://docs.gitlab.com/ci/pipelines/merge_trains/> · <https://bors.tech/>
2. **Batch when several branches are ready** (merge train): merge k gated branches onto a scratch
   integration ref, run the full suite **once**, publish only on green, and bisect by overlapping
   subsets on failure ([1,2] and [1,2,3] in parallel). 4 PRs = 1 CI run (~75% CI saving at 20
   PRs/day). Batch size by failure rate: 5-10 if <2%, 3-5 at 2-5%, 2-3 above 5%; if you bisect more
   than once a day the batch is too large.
   <https://merge-queue.academy/features/batching/>
3. **Speculative merge as pre-flight**: perform the merge in memory (or on a scratch ref) *before*
   integration time purely to detect the conflict early — `git-branchless` does exactly this, and
   `git merge --no-commit` gives a cheap local version. Stopping at merge time is acceptable; being
   *surprised* at merge time is not.
   <https://github.com/arxanas/git-branchless>
4. **`rerere` is reusable text, not validated behaviour.** It replays a recorded resolution for the
   same conflict shape, but it does not re-verify semantics, and it can fail to record at all when a
   file already contains conflict-marker-like lines. A replayed resolution still needs the checks.
   <https://git-scm.com/docs/git-rerere>
5. **Semantic conflicts need behaviour checks, not diff inspection**: a textual merge that succeeds
   says nothing about behaviour. Research prototypes detect them with generated tests as partial
   specifications or control-dependence analysis, but the practical answer for a run is the same:
   **run the suite on the merged result**. <https://spgroup.github.io/papers/semantic-conflicts-testing.html>

## Dependent tasks: stack them, do not serialise the run

When tasks genuinely depend on each other, do not collapse to one long branch, and do not stall the
DAG either:

- **Stacked branches**: each layer targets the branch below; review and land each layer separately.
  `gh stack` (docs: <https://docs.github.com/en/pull-requests/reference/stacked-pull-requests>) and
  `git-machete` (1,139★, <https://github.com/VirtusLab/git-machete>) keep the graph and restack after
  each merge.
- **jj (Jujutsu, 31,626★)** treats conflicts as first-class: a rebase records the conflicted state
  *inside* the commit and still succeeds, descendants auto-rebase, and conflict resolutions in merge
  commits rebase correctly. For a chain of dependent task branches this removes "every rebase stops
  the pipeline". <https://docs.jj-vcs.dev/latest/conflicts/>
- **Sapling (7,013★)** stacks with `absorb` (amend edits into the commit that introduced the lines)
  make restacking nearly free. <https://sapling-scm.com/docs/overview/stacks/>
- **Graphite's merge queue** validates a whole stack in parallel instead of strict one-at-a-time
  ordering — stack awareness is the optimisation, and its own caveat is that strict ordering slows
  merges down. <https://graphite.com/docs/graphite-merge-queue>

## Worktree hygiene (the failure modes that cost runs)

- In a linked worktree `.git` is a **file**, not a directory: anything walking up looking for `.git`
  breaks — use `git rev-parse --show-toplevel`.
- **A branch cannot be checked out in two worktrees at once** — that is exactly the race the skill's
  one-worktree-per-task rule prevents.
- Untracked/ignored files are not copied: copy what the worker needs (env files, generated
  fixtures) explicitly, on purpose, per contract.
- Worktrees parked **inside** the repository are a known cleanup hazard for user tooling; this skill
  keeps them under the run area and reconstructs with `orch.py resume --recreate`.
- Snapshot before deleting a worktree; treat deletion as irreversible.
- <https://www.olafalders.com/2026/09/16/git-worktree-gotchas/> · <https://learn.chatgpt.com/docs/environments/git-worktrees>

## Tooling landscape (what exists, what to borrow)

| Tool | Mechanism worth copying | Gap |
|---|---|---|
| claude-squad (8,488★) | session object = worktree + branch + terminal + process | no queue, no gate |
| vibe-kanban (28,107★) | board column doubles as lifecycle state; inline diff comments routed back to the agent | single machine, no DAG |
| container-use (4,044★) | container per agent, output kept git-native (one branch) | manual merge |
| dmux (1,772★) | lifecycle hooks on worktree-create / pre-merge / post-merge; one-step merge | no test gate |
| worktrunk (7,958★) | `wt merge` + per-branch CI status and LLM summary rollup | infrastructure, not an orchestrator |
| Codex cloud | typed environment config; setup phase separated from agent phase | closed, concurrency caps |
| Devin | approval **before** fan-out; coordinator schema (scope/launch/monitor/compile) | opaque, metered |
| HumanLayer (11,557★) | approval as an out-of-band API (park the request, notify, resume) | Claude-Code specific |
| Orca (70,597★) | fan out one prompt N times, compare, merge the winner; phone notifications | young |
| AgentAPI (1,503★) | turn a TUI agent into a structured message stream by snapshot-diffing | bridge only |
| OpenHands (88,240★) | scheduler service separated from the agent server; pluggable backends | container-per-task, no branches |

**The gap the field leaves open** (this skill's job): almost no tool enforces tests or CI before
merge; review gates are keystrokes. Isolation is commoditised; *gated* integration is not.
