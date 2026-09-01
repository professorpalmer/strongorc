# How to create a benchmark: StrongOrc research notes

The frozen ranking contract is [RANKING.md](RANKING.md). Development
scores used to freeze that contract are in
[CALIBRATION_APPENDIX.md](CALIBRATION_APPENDIX.md). This file keeps the
literature argument and the destup diary. It is not a leaderboard.

The public practice set is `brutal`, `native`, `ladder`, and `reason`.
Public `reason` remains the balanced development instrument. Official
ranking is an off-git private bank: eight families × three
evidence-quality rungs, split 12 orchestrator / 12 worker. The public
object is the SHA-256 commitment
`b4dee106cd5d442e23899c38adf122b54ad82f71163ff36770b7b71f9ee00110`.

The 0.6.0 ranking harness closes the construct failures that made earlier
holdouts unusable:

- orchestrator tasks call a parent-owned worker broker; dispatch and report
  consumption are sealed into `TrialRecord` and cannot be earned by writing
  event vocabulary or `workers_ran`;
- worker tasks execute a frozen orchestrator assignment;
- private generators materialize candidate-visible live evidence before the
  model starts and can revise it after a parent-observed interrupt;
- the ranking headline is strict task pass. Protocol-gated hidden evidence
  is diagnostic. Interrupt survival and protocol vocabulary never add rank;
- provider authentication, payment, rate-limit, and refusal failures are
  coverage, not ability;
- every `(task_id, attempt)` has an isolated run directory and durable jsonl
  key, so repeats survive resume;
- private ids, metadata, authoring code, gold agents, worker pools, and
  oracles stay outside git;
- a public preregistration hash commits to a private file-digest manifest
  before any official ranking response is observed;
- official ranking is the confined OpenRouter jail. `openrouter-shell` is
  historical ablation evidence.

These choices transfer the useful parts of ARC-AGI-2 (private/generated
evaluation and saturation replacement), FrontierMath/LiveBench (unpublished
or post-cutoff items), HLE/SWE-bench Verified (independent review), EvalPlus
(dense deterministic checks), PaperBench (hierarchical diagnostics),
RE-Bench/METR (cost and process reporting), and Zhu et al. 2025 (Agentic
Benchmark Checklist: task validity, outcome validity, and reporting)
without adopting LLM-as-judge.

## Frozen ranking readiness

The ranking-v1 overlay passed structural and scripted preflight: gold
24/24; generic fail, outcome-slip, protocol-slip, assignment-blind, and
protocol-only all 0/24. A nine-system confined matrix on the earlier
frontier-v6 bank identified 2PL, occupied weak/middle/frontier, and
separated the frontier cluster from the middle cluster. That matrix is
development evidence. Official ranks still require a new run on
ranking-v1 after this revision is public.

## What the first confined matrix showed

One OpenRouter jail row (`stealth/ox-alpha`, harness 0.6.0, one attempt)
on every public slice:

| Role | Slice | Tasks | Hidden | Note |
| --- | --- | --- | --- | --- |
| Ranking | reason | 0/12 | 0/96 | played the jail; missed `worker_started` / `artifact_consumed` |
| Ranking | brutal | 0/8 | 0/47 | same hidden floor |
| Ranking | native | 0/12 | 0/96 | same hidden floor |
| Ranking | ladder | 0/48 | 0/384 | same hidden floor |
| Retired | core | 3/12 | ritual | 0 workers on every task |
| Retired | hard | 12/16 | destuped JS | SPEC already called this saturated |
| Retired | frontier | 11/48 | destuped-plus | not a ranking peer of the live four |

Do not destup practice slices up to `reason` to manufacture a rank. They already share the
hidden floor. Do not author holdout in this git tree. Cursor SDK high
scores from this machine are leak diagnostics. OpenCode Go is a
different instrument (no grade verbs). Task-pass family curves look
like zeros on the live set; check grain is the scoreboard.

## What the five-system confined floor showed

2026-08-28–29, same OpenRouter jail, ranking-80, one attempt,
provider-default reasoning. Systems: ox-alpha, Gemini 3.7 flash, Kimi
K3, Sol 5.6, Fable 5. **0/80 task passes** on every system. Weighted
headlines 4–11% are interrupt plus protocol-shape. Hidden is ~0
(Fable reason 1.04% is the first crumb, not a win). IRT is still
unidentified: five zeros is one column. A second confined system was
never the missing piece. A **pass** is.

Interrupt already separates flash floors from kings (Fable ~38% vs
Gemini ~16%). That is a subscale. It is not a ranking of durable
orch. Kings write packages and sometimes survive SIGKILL. They do
not ship the oracle-visible outcome. They also call `wait` on rungs
that never kill.

Do not destup from this matrix. Five confined zeros cannot tell
“items too hard” from “jail is the wall.” First walk-down is
affordance. See the jail-ablation cell below and
[STRONGORC_HISTORY.md](STRONGORC_HISTORY.md).

## Historical note: 2026-08 jail ablation

Same king (Fable), `reason` only, `--jobs 2`, new dest. Channel
`openrouter-shell` adds `run_command` in the run dir. Stamp
`unconfined`. Do not `--fit` with confined OpenRouter jsonl.

| | Hidden still ~0 | Hidden moves / a task passes |
| --- | --- | --- |
| Confined (done) | what we have | we would already have an IRT identifier |
| Shell (sealed) | destup hidden is licensed | the jail was the clamp; keep the 80 |

The threshold is hidden or a task pass, not a higher headline. Shell
Fable reason sealed at hidden 0 / 0/12 with genuine receipts. Destup 1
(2026-08-29): hidden tests resolve Pair / Clinic / Board *or* the same
callable surface (`apply` / `repair` / `resolve`). Destup 2: worker
`artifact_consumed` also accepts probe/discovery events that prove disk
use. Destup 3: consume also accepts worker start/complete; orchestrator
`worker_started` also accepts dispatch events or `workers_ran>=1`. Sealed
interrupt stays. Behavioral cases stay.

Destup 4 is not licensed. Fable's leftover misses are construct: skip
on a broken seal instead of raise (`split_reports` test 003), and a
narrative probe without numeric `a`/`b` (`trace_contract` r3 test 001).
Same-dest regrade after destup 1–3: shell Fable 3/12 hidden 52/96;
confined Fable 3/12 hidden 32/96 (was ~1%). Confined Sol stays 0/12;
confined Kimi stays 0/12. Do not mix those columns. Second shell king (Kimi K3, `--jobs 12`)
sealed 0/12 on destuped reason; two tasks wrote no receipt. Spend is a
report field: `usd_total`, `usd_per_task`, `task_usd` (receipt first,
usage file if receipt is missing or $0). `usd_per_pass` stays total /
passes. Confined OpenRouter 80 remains retired evidence. Do not destup
brutal / native / ladder in this notch.

## What the literature changes

### Define the inference before the score

Construct-validity work argues that validity belongs to the interpretation
made from a score, not merely to the test implementation. StrongOrc may support
the inference “this system handled these durable-orchestration failure classes
under this adapter and harness.” It does not support “general agent
intelligence,” “coding ability,” or a product-wide capability score.

Actions:

- Add an explicit validity argument and non-claim list to the specification.
- Map every task family to a durable-orchestration sub-construct.
- Remove task families whose success is explained mainly by ordinary package
  implementation.
- Validate convergence against real orchestration incidents and discriminate
  StrongOrc from SWE-style artifact repair.

Primary sources:

- Raji et al., “AI and the Everything in the Whole Wide World Benchmark,”
  2021, https://arxiv.org/abs/2111.15366
- Bowman and Dahl, “What Will it Take to Fix Benchmarking in Natural Language
  Understanding?”, 2021, https://arxiv.org/abs/2104.02145
- Bean et al., “Measuring what Matters: Construct Validity in Large Language
  Model Benchmarks,” 2025, https://arxiv.org/abs/2511.04703
- Cronbach and Meehl, “Construct Validity in Psychological Tests,” 1955,
  https://doi.org/10.1037/h0040958

### Treat benchmark quality as a lifecycle

BetterBench evaluates design, implementation, documentation, maintenance, and
retirement. StrongOrc has an official keyless scorer and explicit version
incomparability, but lacks a complete datasheet, release replication job,
feedback path, and retirement registry.

Actions:

- Maintain one registry index with slice, harness version, contamination
  status, comparable series, and retirement reason.
- Archive frozen trials beside every card and verify card regeneration in CI.
- Publish a datasheet for task provenance, intended uses, limitations, and
  maintenance.
- Retire `hard` and `frontier` as evidence-only saturated slices.

Primary sources:

- Reuel et al., “BetterBench: Assessing AI Benchmarks, Uncovering Issues, and
  Establishing Best Practices,” 2024, https://arxiv.org/abs/2411.12990
- Gebru et al., “Datasheets for Datasets,” 2021,
  https://arxiv.org/abs/1803.09010
- Mitchell et al., “Model Cards for Model Reporting,” 2019,
  https://doi.org/10.1145/3287560.3287596
- Biderman et al., “Lessons from the Trenches on Reproducible Evaluation of
  Language Models,” 2024, https://arxiv.org/abs/2405.14782

### Assume public tests will become training data

Plaintext hidden tests and reference implementations are not a durable
anti-contamination strategy. Relocating the run directory protects against
path traversal by a confined command adapter; it does not hide the checkout
from Cursor SDK.

Actions:

- Never accept registry cards from an agent that can read the benchmark tree.
- Keep the registry holdout and its generators outside the public repository.
- Add a benchmark canary and a per-card contamination status.
- Date-stamp generated item banks and score models against post-cutoff items.
- Use the public ladder only for development and oracle examples.

Primary sources:

- Jacovi et al., “Stop Uploading Test Data in Plain Text,” 2023,
  https://aclanthology.org/2023.emnlp-main.308/
- Sainz et al., “NLP Evaluation in trouble,” 2023,
  https://aclanthology.org/2023.findings-emnlp.722/
- Jain et al., “LiveCodeBench,” 2024/2025,
  https://arxiv.org/abs/2403.07974
- White et al., “LiveBench,” 2024/2025,
  https://arxiv.org/abs/2406.19314
- Srivastava et al., “Beyond the Imitation Game,” 2022,
  https://arxiv.org/abs/2206.04615

### Calibrate difficulty empirically

The labels r1–r4 are author-assigned transformations, not measured item
difficulty. Item response theory distinguishes difficulty from discrimination:
an item can be hard while still failing to separate systems, or easy while
being highly informative around a useful ability range.

Actions:

- Collect a same-harness response matrix across weak, middle, and frontier
  systems.
- Fit task-level or check-level 2PL item response models.
- Drop or rewrite near-zero-discrimination items.
- Use evidence-quality rungs rather than width rungs.
- Consider adaptive item selection only after stable item parameters exist.

Primary sources:

- Rodriguez et al., “Evaluation Examples are not Equally Informative,” 2021,
  https://aclanthology.org/2021.acl-long.346/
- Vania et al., “Comparing Test Sets with Item Response Theory,” 2021,
  https://aclanthology.org/2021.acl-long.416/
- Polo et al., “tinyBenchmarks,” 2024,
  https://arxiv.org/abs/2402.14992

### Model uncertainty at the task boundary

Hidden checks within one task share a package, process, prompt, and failure.
Treating 384 ladder checks as independent Bernoulli observations produces
intervals that are too narrow. Model comparisons should use paired item-level
differences and a power calculation.

Actions:

- Make task-clustered bootstrap intervals the primary uncertainty.
  Widen unanimous all-pass / all-fail clustered intervals with a
  task-level Wilson envelope so they are not `[1, 1]` or `[0, 0]`.
- Report task-equalized and check-weighted scores side by side.
- Require at least three attempts for live registry cards.
- Pre-register the smallest meaningful score difference and required sample.
- Do not rank systems when paired uncertainty does not separate them.

Primary sources:

- Miller, “Adding Error Bars to Evals,” 2024,
  https://arxiv.org/abs/2411.00640
- Card et al., “With Little Power Comes Great Responsibility,” 2020,
  https://aclanthology.org/2020.emnlp-main.745/

### Audit deterministic oracles

StrongOrc correctly avoids LLM-as-judge. Deterministic tests can still be
wrong, over-specific, or hollow. SWE-bench Verified discarded most sampled
items after expert review; EvalPlus showed that denser tests substantially
change pass rates.

Actions:

- Require two independent reviewers for every private family.
- Record disagreements and underspecification.
- Generate metamorphic cases at grade time.
- Keep a named scripted fail for every fail class.
- Preserve LLM-as-judge only as a negative control, never an oracle.

Primary sources:

- OpenAI and SWE-bench authors, “Introducing SWE-bench Verified,” 2024,
  https://openai.com/index/introducing-swe-bench-verified/
- Liu et al., “EvalPlus,” 2023, https://arxiv.org/abs/2305.01210
- Northcutt et al., “Pervasive Label Errors in Test Sets Destabilize Machine
  Learning Benchmarks,” 2021, https://arxiv.org/abs/2103.14749
- Zheng et al., “Judging LLM-as-a-Judge,” 2023,
  https://arxiv.org/abs/2306.05685

## Next instrument: the private reason slice

Working name: `reason` or `apex`.

The slice should contain 8–12 independently generated tasks, split across O
and W tracks. Its rungs change evidence quality and required inference, not
the number of files or kills:

- L0: trust the live spec and ignore planted prose. This is the saturated public
  ladder floor and is excluded from the apex headline.
- L1: induce a contract from partial traces because decisive spec fields are
  absent.
- L2: revise that induced contract after sealed contradictory evidence.
- L3: recognize underdetermination and dispatch a discriminating probe before
  acting.
- L4: evaluate against an unpublished metamorphic generator.

Candidate families:

1. `trace_contract`: infer the invariant from worker traces and examples.
2. `retract_rule`: revise a previously successful rule after a post-kill
   counterexample.
3. `split_reports`: resolve mutually inconsistent worker receipts using sealed
   hashes and causal eligibility, not majority or recency.
4. `diagnose_kill`: identify one real cause among stale lease, dead child, cap,
   and hash-drift decoys, then repair only that cause.
5. `fence_horizon`: compose state across at least five mutations and kills
   rather than applying only the final rewrite.
6. `budget_pareto`: choose cancellations and refusals under a live policy where
   completeness, cost, and honesty cannot all be maximized.
7. `alloc_leases`: allocate heterogeneous jobs under changing caps and prices;
   grade regret against the policy optimum.
8. `probe_partial`: discover an omitted field by scheduling a probe worker;
   guessing or reading prose fails.
9. `belief_series`: carry a sealed belief digest and failed-check evidence into
   a later trial, then demonstrate a changed prediction.
10. `meta_cases`: infer a grammar from examples and pass nonce-generated cases
    never stored in git.

Oracle constraints:

- No LLM judge.
- No hidden tests or reference implementations in the public tree.
- Grade-time generated cases keyed by a harness nonce.
- Opaque public test identifiers.
- Harness-sealed kill and worker-report evidence.
- Structural provenance for who produced artifacts; no self-reported
  “orchestrator did not play” event as the only proof.
- A gold agent that interprets live objects rather than copying a reference.

Expected failure signatures:

- Trusting README or the first spec.
- Majority-voting conflicting reports.
- Applying both hypotheses instead of probing.
- Fixing the symptom rather than the causal node.
- Replaying a prior answer after contradictory evidence.
- Implementing only the last rewrite in a long horizon.
- Completing all work despite a refusal policy.
- Overfitting examples instead of inducing their grammar.

Calibration protocol:

1. Scripted interpreter pass must score 1.0; a targeted scripted fail must miss
   a named check.
2. Run the same harness SHA and confined adapter with at least three attempts.
3. Include at least two weak, two middle, and two frontier systems.
4. Publish task pass, family pass, rung curves, task-equalized score,
   check-weighted evidence, cost, attempts, and clustered intervals.
5. Target weak systems below 0.15, middle systems around 0.15–0.40, and
   frontier systems around 0.35–0.70 on the private slice.
6. If frontier systems exceed 0.80–0.90 or weak and frontier systems tie,
   redesign the family instead of adding width.
7. Fit item difficulty and discrimination only after collecting the response
   matrix; do not call authored rungs calibrated beforehand.

The instrument is `strongorc calibrate` / `scripts/calibrate.py`. One
jsonl is one system. The response for each task is its gated evidence
rate; strict task pass remains a separate reported field. Scripted
pass/fail yields status `oracle_nonvacuity`, is excluded from empirical
curves, and does not identify IRT parameters. Three to five live systems
yield Rasch and status `underpowered`. Six or more live systems with item
variance yield 2PL and status `fitted`. Items with negative
point-biserial are `drop`; near-zero `a` or point-biserial are `rewrite`.
Pre-registration for the
Cursor SDK leak-diagnostic channel lives at
`cards/preregister/reason-0.6.0.json`. The confined OpenCode Go channel
is `cards/preregister/reason-0.6.0-opencode-go.json`
(`--channel agentic-opencode`). Do not mix those series. Do not register
authoring-machine cards as clean.

## What a truly frontier instrument requires

Public `reason` is still too close to “read the traces and implement.”
Grok 4.6 Extra High + Fast clearing 11/12 on the authoring machine is
above the 0.80–0.90 rewrite line even before treating that row as a
leak. A frontier orchestration bench is not a harder sibling of SWE-style
artifact repair. The 2024–2026 literature converges on a short list of
requirements that StrongOrc has only partly met.

### 1. Define a construct that does not collapse to coding

Raji et al. (2021) warn against “everything in the whole wide world”
benchmarks. Bean et al. (2025) treat construct validity as the primary
failure mode of LLM evals. Bowman and Dahl (2021) argue that progress
requires the claim to be stated before the score is published. A
frontier StrongOrc item must fail a strong coder who does not induce
the live contract, and pass only a system that treats durable state as
the object of inference.

Actions: drop families whose gold is ordinary package implementation;
keep only fail classes that change under sealed evidence, leases,
receipts, or underdetermination.

### 2. Assume the public set will be trained on

Jacovi et al. (2023) and Sainz et al. (2023) treat plaintext test data
as contamination by default. LiveCodeBench (Jain et al., 2024) and
LiveBench (White et al., 2024) date-stamp items after model cutoffs.
GSM-Symbolic (Mirzadeh et al., 2024) shows that template-stable public
math items overstate competence once surface numbers change. SWE-bench
Verified discarded most sampled items after expert review because the
tests did not measure the intended repair. A public `reason` tree with
plaintext `hidden/` is a development floor, not a frontier instrument.

Actions: keep the publishable item bank off git; generate cases at
grade time from a harness nonce; canary public tests; never accept a
Cursor SDK row from a machine that can open this checkout.

### 3. Make items hard by underdetermination, not width

Grok saturating `ladder` r1–r4 and then `reason` r1–r3 on the
authoring machine is the same lesson twice. Adding lanes, kills,
decoys, or r5 constants does not create a frontier construct.
FrontierMath (Glazer et al., 2024) and Humanity’s Last Exam (Phan et
al., 2025) buy headroom by asking unpublished expert problems, not by
cloning easier siblings. ARC-AGI-2 and PaperBench (OpenAI, 2025) grade
whether the system discovered a rule it was not handed. Terminal-Bench
keeps a long horizon, but the hard items are underspecified environments,
not more keystrokes.

Actions: rungs must revoke evidence, plant contradictions, or require
a probe. If a frontier system exceeds 0.70–0.80 on a confined channel,
rewrite the family.

### 4. Do not run a generic leaderboard

Singh et al., “The Leaderboard Illusion” (2025) show that private
retries, selective disclosure, and uneven sampling turn a ranking into
an overfitting contest. BetterBench (Reuel et al., 2024) treats
retirement as part of the lifecycle. StrongOrc already refuses a
product `capability_score` and keeps slice + harness version in the
quote. The remaining failure mode is mixing channels: Cursor SDK leak
rows, confined OpenCode Go rows, and OpenRouter cash rows are not one
series.

Actions: one pre-register file per channel; quarantine saturated
slices; no Chatbot-Arena-style retract-and-retry; publish only after
the same-harness matrix exists.

### 5. Calibrate items; report uncertainty at the task boundary

Rodriguez et al. (2021) and Vania et al. (2021) show that items are
not equally informative. Miller (2024) requires error bars. Card et
al. (2020) require a power calculation before a ranking. Authored
r1–r3 labels are not difficulties. A 11/12 leak row does not identify
2PL parameters.

Actions: same-channel weak / middle / frontier matrix; task-clustered
intervals; three attempts before a registry card; drop
zero-discrimination items instead of averaging them away.

### 6. Keep the oracle deterministic and reviewed

EvalPlus (Liu et al., 2023) and Northcutt et al. (2021) show that
tests, not models, are often the unstable object. LLM-as-judge (Zheng
et al., 2023) is a negative control here, never the grade. SWE-bench
Verified is the existence proof that expert review shrinks a bench.

Actions: two reviewers on every private family; named scripted fail
per fail class; metamorphic cases at grade time.

Primary sources added here:

- Singh et al., “The Leaderboard Illusion,” 2025,
  https://arxiv.org/abs/2504.20879
- Mirzadeh et al., “GSM-Symbolic,” 2024,
  https://arxiv.org/abs/2410.05229
- Glazer et al., “FrontierMath,” 2024,
  https://arxiv.org/abs/2411.04872
- Phan et al., “Humanity’s Last Exam,” 2025,
  https://arxiv.org/abs/2501.14249
- Starace et al., “PaperBench,” 2025,
  https://arxiv.org/abs/2504.01848
- Chowdhury et al. / Stanford / Laude, Terminal-Bench,
  https://www.tbench.ai/
- Bowman, “Eight Things to Know about Large Language Models,” 2023,
  https://arxiv.org/abs/2304.00612

## Immediate instrument work before a public table

1. Publish this revision: harness, scoring rules, ranking commitment, and
   labeled calibration appendix. Keep the private bank off git.
2. Get CI green on `dev`, then run official ranking-v1 attempts.
3. Do not destup public practice oracles to manufacture a rank.
4. Do not add r5 or r6 mechanical ladder constants.
5. Refuse every paid live run without structural/scripted preflight and
   an explicit per-task USD cap. Concurrency above two is an override,
   never a default.
6. Keep authoring-machine Cursor SDK cards as leak diagnostics.

## Publication sequence

The how-to narrative and the StrongOrc research paper are different artifacts.

1. This revision freezes harness 0.6.0, the ranking-v1 commitment, and the
   scoring rules. Calibration rows stay labeled development evidence.
2. Keep citation metadata, datasheet, frozen trial replication, and CI gates
   current with the tagged tree.
3. Tag a green release from `main` only after CI is green on that tree.
4. Archive that exact tag on Zenodo and cite the version DOI. GitHub plus
   Zenodo is the first citable object (BetterBench lifecycle; Gebru
   datasheet; Mitchell model-card spirit applied to the bench, not the
   systems).
5. Run official ranking only after that freeze is public. Do not change
   the bank while scoring.
6. Publish a research article titled around “StrongOrc: Measuring Durable
   Orchestration” only after ranking-v1 results exist. The paper’s claims
   are the validity argument, the item-response evidence, and the
   non-claim list — not a generic agent ranking.
7. Keep the public card registry self-hosted. Do not flatten slice,
   harness version, and channel into a Chatbot-Arena-style leaderboard
   (Singh et al., 2025).

GitHub plus Zenodo is the first citable release path. arXiv is appropriate
for the later construct, method, results, and limitations paper.

