# Budget, model routing and cache-aware dispatch

An orchestrator that spends without limits is not orchestrating, it is gambling. This file is the
policy layer: how to pick the model, how to keep the cache hot, and how to stop.

## The fan-out gate (apply before any parallel dispatch)

Parallelism costs about an order of magnitude more tokens than a chat turn, so it must be justified:

- Anthropic's production numbers: agents ~**4x** chat tokens, multi-agent systems ~**15x**; token
  usage alone explained **80%** of performance variance. Their guidance: multi-agent pays off only
  where the task value is high enough to absorb the multiple.
  <https://www.anthropic.com/engineering/multi-agent-research-system>
- Independent measurement of fan-out vs sequential: **2.6x-5.9x input tokens, never faster**.
  <https://systima.ai/blog/subagent-tax>
- Cursor's A/B across millions of requests: routing to a cheaper tier matched a frontier model on
  user satisfaction at **~60% lower cost**; measured cost per commit $4.63 (balanced) vs $7.34
  (all-frontier). <https://cursor.com/guides/model-routing>

**Gate**: fan out only if (a) tasks are genuinely independent, (b) the value justifies ~10x tokens,
and (c) the slices have disjoint `write_scope`. Otherwise stay single-agent. Then cap it:
`max_parallel_workers` (default 3, ceiling 5-8), delegation **depth 1** unless a recorded reason
justifies 2, and no unbounded "spawn a verifier per finding" loops.

## Model ladder: pin per task class, never inherit

| Rung | Task classes | Price anchor |
|---|---|---|
| cheap | mechanical edits, renames, extraction, formatting, summaries, boilerplate tests, log reading | Haiku-class ~$1/$5 per MTok |
| mid | single-file features, test fixes, focused debugging | Sonnet-class ~$2-$3/$10-$15 |
| top | planning, architecture, cross-module refactors, hard debugging, **review** | Opus-class ~$5/$25+ |

The spread between cheapest and most expensive rung on the same provider surface is ~**50x** input
price — the same job on the wrong rung is a 10-50x cost difference, not a rounding error.
<https://platform.claude.com/docs/en/about-claude/pricing> ·
<https://platform.openai.com/docs/pricing>

Rules:
1. **Pin the model in the worker's own definition.** An inherited model silently runs cheap workers
   on the session's expensive model (Claude Code subagents gained a per-subagent `model` field, and
   the built-in Explore agent changed to inherit — fan-outs run on whatever the session drives).
   <https://code.claude.com/docs/en/sub-agents>
2. **Never swap the model mid-run to save money.** A mid-conversation model change misses the prompt
   cache; a naive before/after ignores that cost entirely.
   <https://cursor.com/guides/model-routing>
3. **Use the ladder as the escalation path**: a worker that spins twice escalates one rung (recorded
   in `worker_history`), rather than being replaced by an equally cheap worker.
4. Model choice is part of the run state (it survives recovery) — see the skill's bootstrap step.

## Prompt cache: the largest single lever on input cost

- Anthropic: cache **writes cost 1.25x** (5-minute TTL) or **2x** (1-hour), **reads cost 0.1x**
  (0.025x on the newest models). The cache follows the hierarchy **tools → system → messages**;
  changing tool definitions invalidates everything after.
  <https://platform.claude.com/docs/en/build-with-claude/prompt-caching>
- OpenAI: same economics (1 write + 9 reads = **2.15x** vs 10x uncached ≈ **-78.5%**), TTFT down up
  to 80%, input cost down up to 90%. Compaction **rewrites earlier context and resets reuse** from
  the first changed token.
  <https://platform.openai.com/docs/guides/prompt-caching>
- Minimums matter: 1,024 tokens on GPT-5.6+; 512 (Opus 5/Fable) to 2,048-4,096 (older Claude);
  hits occur in 128-token increments. A worker prompt below the minimum caches nothing.
- TTL is a **scheduling** constraint: the default 5-minute window starts when the request that
  writes the entry arrives, so a slow worker wave can outlive the cache and re-prime the whole
  prefix at full price. Dispatch a wave **together**; use the 1-hour tier only for long-lived
  workers that amortise the 2x write.
- **Gemini/Gemma-style implicit caching** is on by default (min 2,048-4,096 tokens) and reports hits
  in `usage.total_cached_tokens` — verify, do not assume.

**Cache-aware orchestration (rules):**
1. One **byte-stable prefix per worker**: canonical order tools → system → messages; identical tool
   schemas across workers of a wave; no top-of-prompt timestamps or random IDs.
2. **Append-only turns.** Never rewrite earlier turns or reorder messages mid-run.
3. **Compaction is a wave boundary**, not a mid-flight action: it invalidates reuse from the changed
   token onward.
4. **Dispatch workers of a wave together**, inside the TTL.
5. **Log cache economics per run** (write tokens, read tokens, hit share) as a first-class budget
   line — Claude Code surfaces it as "Prompt cache (main)" in `/usage`.
   <https://developers.openai.com/cookbook/examples/prompt_caching_201>
6. Expect cache-hit share to vary by provider routing; a low hit share is a prompt-construction bug,
   not bad luck.

## Handoff payload: the 4-part contract, summaries only

- Every delegation carries: **objective, output format, tools/sources to use, explicit boundaries**.
  Vague briefs produce duplicated and misread work (one agent researched the 2021 chip crisis while
  two duplicated 2025 supply chains in the same run).
  <https://www.anthropic.com/engineering/multi-agent-research-system>
- **Workers absorb the noise; the parent gets the summary.** The orchestrator's context is re-billed
  on every step, so 100k tokens of raw tool output avoided saves 100k × remaining steps.
  <https://code.claude.com/docs/en/sub-agents>
- **Keep the always-loaded index small**: Claude Code warns past **15,000 tokens** of combined
  subagent descriptions and tells you to move detail into each subagent's system prompt (progressive
  disclosure). Same rule for skills and MCP tool schemas.
- **Never hand over raw logs, whole files or the full conversation.** Context rot is measured:
  performance degrades as input grows even on trivial tasks, and a single distractor already hurts
  (18 models incl. GPT-4.1/Claude 4/Gemini 2.5). <https://research.trychroma.com/context-rot>
- **Put the load-bearing spec at the top or bottom**, never buried mid-payload — "lost in the
  middle" is measured, not folklore. <https://arxiv.org/abs/2307.03172>
- **Bulky artifacts go to the filesystem**; pass paths and hashes, not bodies (Anthropic's artifact
  system: prevents "game of telephone" fidelity loss and coordinator bloat).
- **Share full traces only where coupling demands it**: tightly coupled work goes to one agent;
  independently verifiable slices get summary handoffs. Cognition's point — actions carry implicit
  decisions that a merger cannot reconcile.
  <https://cognition.ai/blog/dont-build-multi-agents>

## Budget enforcement mechanics

| Mechanism | How | Source |
|---|---|---|
| **Per-run hard cap** | a dollar/token ceiling enforced by the harness, with subagent spend counted in the parent's budget; refuse new spawns and stop running workers when exceeded | Claude Code `--max-budget-usd` semantics <https://code.claude.com/docs/en/costs> |
| **Per-task step cap** | `max_turns`/iteration ceiling per worker, recorded in the contract | Agents SDK `max_turns` |
| **Kill switch** | watchdog detects budget exhaustion → stop the worker, checkpoint, escalate; never "one more attempt" | this skill's watchdog |
| **Provider hard limits** | spend-limit responses (OpenAI 429 spend-limit codes) and per-key credit limits (OpenRouter) as the backstop | <https://platform.openai.com/docs/guides/error-codes> |
| **Gateway budgets** | key/agent budgets in a proxy (LiteLLM); caveat: fail-open without a DB | <https://docs.litellm.ai/docs/proxy/users> |
| **Cost observability per task** | tokens in/out, cache reads, model, wall time, retries — per task *and* per run | Claude Code `/usage` + OTel export |

Budget anchors from measured enterprise deployments: **~$13 per developer per active day**,
**$150-250/month**, with 90% of users under $30/active day. Start with a pilot, then set caps.
<https://code.claude.com/docs/en/costs>

## Steer on cost per accepted outcome

Token price is a proxy; the metric that matters is **cost per merged, surviving change**:

- AI-assisted PRs run **~18.2% larger** and review time can climb **~91%** — so "cost per token"
  can look cheap while cost per merged PR rises. Divide fully-loaded AI cost (tokens + tools + review
  time + rework) by PRs that merge and survive a churn window.
  <https://getunblocked.com/blog/cost-per-merged-pr>
- Cursor's equivalent: cost per commit ($4.63-$6.76 measured).
- Artificial Analysis's coding-agent index shows the same harness swinging **$0.24 to $12.4 per
  task** purely by model choice — place each task class on the cheapest rung that still resolves it,
  measured, not guessed. <https://artificialanalysis.ai/agents/coding-agents>

## What to record per run (the numbers that make the next plan cheaper)

```yaml
run_metrics:
  tasks_dispatched / tasks_merged
  tokens_in / tokens_out / cache_read_share      # per task and per run
  model_per_task                                  # which rung was used, and why
  wall_time_per_task
  dispatches_per_accepted_task                    # rework signal
  review_fail_rate / fix_cycles_used
  spin_events / replacements / escalations
  budget_cap_usd / budget_used_usd
  cost_per_accepted_change
```

A run that cannot report these cannot be improved. They are also the input to the skill's proposal
loop (`orch.py propose`).
