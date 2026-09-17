# Provable done: verifying LLM work

The producer's transcript is **not** evidence. This file lists what to do instead, with the measured
numbers behind each technique.

## Why the producer cannot be trusted (the baseline facts)

- Agents **assert completion while the environment contradicts them**: 45-48% of failures in
  tau2 single-control domains, **75.8% of self-assessing AppWorld coding trajectories**.
  <https://arxiv.org/abs/2606.09863>
- **LLM judges are poor at detecting exactly that**: across 5 judges and 5 prompt strategies, none
  exceeded **AUROC 0.65** on tau2-bench (0.54 on AppWorld traces) — they key on confident closing
  language. A calibrated TF-IDF detector reached **0.83/0.95** task-disjoint AUROC at ~3300x lower
  latency: use cheap calibrated detectors for triage, not judges for verdicts.
  <https://arxiv.org/abs/2606.09863>
- **Self-correction without external feedback is unreliable or harmful**: "LLMs struggle to
  self-correct their responses without external feedback, and at times their performance even
  degrades after self-correction" <https://arxiv.org/abs/2310.01798>; GPT-4's iterative
  self-critique *degraded* Game-of-24 and planning, while a sound external verifier produced large
  gains <https://arxiv.org/abs/2402.08115>.
- **Do not gate task flow on the agent's own progress reports**: nearly every model is reliable at
  some stages and unreliable at others (most lose accuracy mid-task; newer models grow conservative
  at the finish line). <https://arxiv.org/abs/2609.08589>
- **Repair loops can do net damage**: LLMs claim to find bugs in bug-free programs while their
  repair rate is *lower than their damage rate* to correct programs, and loops reach a
  pseudo-bug-fixing cycle (same change added and removed indefinitely).
  <https://arxiv.org/abs/2609.10123>

## Layer 1 — evidence the orchestrator captures itself

| Technique | What it catches | Cost |
|---|---|---|
| **Clean-room re-execution**: replay the committed patch on the pinned `base_commit` in a fresh checkout/container and run the checks there | success that depended on the producer's session (dirty tree, untracked files, ad-hoc installs, local config) | one checkout + one suite run |
| **Differential gate (FAIL_TO_PASS / PASS_TO_PASS)**: require named tests to flip red→green *and* previously-passing tests to stay green | "tests pass" claims where nothing actually changed | two suite runs |
| **Orchestrator-owned capture**: record command, exit code, artifact hash outside the agent's shell | fabricated or smoothed-over evidence; false completion behind a success flag | trivial |
| **Test-artifact immutability**: restore test paths from `base_commit` before grading; quarantine any diff hunk under `tests/`, CI config, or fixtures for explicit approval | green-by-weakening (deleted/skipped tests, relaxed assertions, changed expected values) | git checkout + path filter |

Sources: SWE-bench harness and dataset design <https://github.com/SWE-bench/SWE-bench/blob/main/docs/reference/harness.md>
· <https://github.com/SWE-bench/SWE-bench/blob/main/docs/guides/datasets.md> · evidence-carrying
termination <https://arxiv.org/abs/2608.23623> (0/288 unsafe completions vs 252/288 for a
termination-critic baseline; 0/66 premature unsupported terminations vs 40/66) · SWE-Bench+ finding
that **31.08%** of accepted patches were "suspicious" because the tests were too weak, and 32.67% of
"successful" patches were cheating <https://arxiv.org/abs/2410.06992>.

Legitimate test edits exist (new fixtures, interface changes). They are not auto-rejected — they are
**escalated**: the diff hunk is shown, the reason is recorded, and the immutability rule is waived
explicitly, never silently.

## Layer 2 — independent review that actually finds things

- **Independence is structural**: a different model family / agent / harness than the producer, and
  the producer never authors or grades the rubric. Same-family reviewers structurally favour the
  producer's style (GPT-4 scores low-perplexity text higher regardless of author —
  <https://arxiv.org/abs/2410.21819>; MT-Bench documents self-enhancement plus verbosity bias —
  <https://arxiv.org/abs/2306.05685>).
- **Position bias is large**: reordering candidates alone let Vicuna-13B "beat" ChatGPT on **66/80**
  queries under GPT-4 judging. Running pairwise comparisons in both orders and aggregating
  (Balanced Position Calibration), plus requiring evidence before the score (Multiple Evidence
  Calibration), restored agreement with human judgement. <https://arxiv.org/abs/2305.17926>
- **Specialised critics beat generic self-review**: RLHF-trained critics were preferred over human
  critiques in 63% of cases and found more bugs — but they also hallucinate bugs and can mislead
  humans into unnecessary fixes. <https://arxiv.org/abs/2407.00215>
- **Anti-anchoring**: reviewers handed AI-flagged lines concentrate there and miss defects elsewhere
  (controlled experiment, 29 experts, 50+ hours). Either run an independent sweep first, or have a
  second reviewer who never sees the first report. <https://arxiv.org/abs/2411.11401>
- **Harden the reviewer against framing/injection**: crafted PR metadata biased real LLM review
  pipelines across 33 CVEs in 20 projects. Strip producer-written narrative from the review prompt;
  require findings to cite `file:line` and the diff hunk. <https://arxiv.org/abs/2603.18740>
- **Counterfactual findings**: a claimed bug/fix should come with an executable consequence —
  accept the finding only if applying the proposed fix actually changes observed behaviour
  (fix-guided filter). Catches the common LLM failure of "fixing" correct code.
  <https://www.researchsquare.com/article/rs-8993044/v1>
- **Independence is necessary but not sufficient**: N-version programs fail together (Knight &
  Leveson 1986, DOI 10.1109/TSE.1986.6312924), and common-mode failure clusters where the spec is
  ambiguous. Budget repeated trials and **escalate low-agreement items** to the user instead of
  averaging them away. <https://arxiv.org/abs/2606.20158>
- **Weak-verifier ensembles** beat single judges for picking among N attempts (weighted ensembles
  of weak verifiers pushed a 70B generator to o3-mini-level selection accuracy).
  <https://arxiv.org/abs/2506.18203>

## Layer 3 — objective quality gates that do not reduce to "a test ran"

| Gate | Evidence | Where it fails |
|---|---|---|
| **Property-based testing** (invariants + generated inputs, minimal counterexample returned to the producer) | +13.4% pass@1 over TDD baselines; hybrid property+example testing 81.25% vs 68.75% bug detection | property quality is the bottleneck; weak properties pass wrong code |
| **Metamorphic testing** (assert relations between executions when no oracle exists) | industry answer to "the number looked fine" | relations can be weak; a wrong relation is a false alarm |
| **Mutation testing** (kill mutants, feed survivors back as test requirements) | mutant detection correlates with real-fault detection *independently of coverage* (357 real faults, 321k LOC); LLM-generated mutants find 111.29% more real bugs; Meta's ACH generated tests with 73% engineer acceptance | compute cost; equivalent mutants; needs triage |
| **Coverage** | — | demoted to a **diagnostic only**; it does not correlate with fault detection |

Sources: <https://arxiv.org/abs/2506.18315> · <https://arxiv.org/abs/2510.25297> ·
<https://dl.acm.org/doi/10.1145/2635868.2635929> · <https://dl.acm.org/doi/10.1145/3143561> ·
<https://arxiv.org/abs/2406.09843> · <https://arxiv.org/abs/2501.12862>

## Layer 4 — reliability, not luck

- **pass^k, not pass@1**: tau-bench showed a strong agent solving <50% of tasks with **pass^8 <25%**
  in retail — the same task failed most of the time when repeated. A single green run is not
  evidence of a working change. <https://arxiv.org/abs/2406.12045>
- **Report reliability horizons** (50% vs 80% success) rather than "capable"; recent capability
  gains have come mainly from reliability and error recovery. <https://arxiv.org/abs/2503.14499> ·
  <https://metr.org/time-horizons/>
- **Fix-loop guardrail**: no fix without a reproducing failure; cap iterations (the skill's
  `max_fix_cycles`); re-run the **full** suite every pass so a repair cannot silently regress
  something else; escalate ambiguity instead of looping.
- **Holdout discipline + cost accounting**: keep a private held-out task set and report cost next
  to success — benchmarks without holdouts and accuracy-only reporting are how an agent "looks
  done". <https://arxiv.org/abs/2407.01502>
- **Contamination probes**: models identify buggy files from issue text alone at up to **76%** on
  SWE-bench Verified vs 53% elsewhere; dropping contaminated instances cut resolution from 12.47% to
  3.97%. When a worker resolves something suspiciously fast, ask whether the answer was in the
  context (issue text, comments, vendored copy) rather than derived.
  <https://arxiv.org/abs/2506.12286> · <https://arxiv.org/abs/2410.06992>
- **Harness configuration is a variable**: the same task set swings cost and score with harness
  settings, so record model + harness configuration with every result.
  <https://arxiv.org/abs/2601.11868> · harness-bench.ai

## Applied to this skill

1. The **result contract** is communication. `orch.py verify` + the orchestrator's own command
   output are evidence.
2. `required_checks` in the contract must name commands whose **exit code** is captured, not
   assertions of success.
3. The reviewer receives the **review package** (contract + diff + captured evidence), never the
   worker's chat narrative, and must return findings that cite `file:line`.
4. A FAIL returns to the responsible worker; the fix loop requires a **reproducing failure** and is
   bounded; after the cap, escalate.
5. Test-path edits are quarantined and escalated, never silently accepted.
6. For high-risk or flaky slices, require **repeat runs** before the merge gate can be ready; a
   single green pass is recorded as `tests: pass (n=1)` and the gate policy decides whether that is
   enough.
