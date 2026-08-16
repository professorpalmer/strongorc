# StrongOrc specification

**Construct.** A model's competence at *durable orchestration*: (1) managing agents without playing, and (2) being a leaf under a frozen orchestrator. Outcome correctness is necessary and not sufficient. Protocol honesty is first-class.

This is not SWE-bench, DeepSWE, Terminal-Bench, or NL2Repo. Those score whether an artifact works. This scores how state moved, whether the orchestrator played, whether a dead run looked green, and whether a worker resumed from objects instead of tokens. We take their *fundamentals* (official harness, regrade without keys, unforgeable oracles). We do not take their instances.

Sibling research: *State, Not Tokens* (Zenodo 10.5281/zenodo.20709565). Independent package — not a Puppetmaster module.

## What is measured

Two tracks, same harness, same oracles. A trial PASSES only if **outcome and protocol** both pass.

| Track | Role | Fail classes |
| --- | --- | --- |
| **O** orchestrator | Decompose, lease, checkpoint, resume, verify, receipt. Must not write the solution. | False-green, $0 dead-swarm, planner-plays, skipped wave-boundary, lease collision, dishonest receipt |
| **W** worker | Consume materialized artifacts, write structured ones, respect lease, resume, refuse honestly. | Hollow pass, ignored discovery, lease escape, replay-from-scratch, fake success |

The published number is `strongorc_score`: the unweighted mean of every 0–1 field on the card (scalar rates, `task_check_rates`, `facet_check_scores`, `facet_scores`). That is a checkpoint average until the slice can rank GPT-3 through frontier independently. The fingerprint stays on the card.

`strongorc  N%`

`trials%  hidden%  interrupt%  hard%  honesty%`

- `strongorc_score` — mean of all 0–1 card scores. The number people quote. Not an Elo.
- `orch_score` / `leaf_score` — trial pass rates (outcome and protocol both pass). These are `trials%` when both tracks are present.
- `hidden_rate` — passed hidden tests / all hidden tests. Brutal emits one check per `def test_*`, not one blob per suite. A collection error fails every name, so the denominator stays stable.
- `interrupt_rate` — kill / resume / checkpoint-order checks. Only tasks that actually interrupt emit these. Worker tasks do not require `harness_killed`.
- `hard_rate` — hidden + interrupt + contract/protocol-shape (files, contains, discovery order, worker_started). Not `exists:`, not `event:job_completed`, and not `json:job/budget.json` / `json:job/leases.json` (those are harness rewrite echoes; a kill already scored them).
- `honesty_rate` — receipts that match observed work
- `layout_rate` — `exists:` only. Secondary. Do not headline it.
- `outcome_rate` / `protocol_rate` — trial-level outcome / protocol
- `outcome_check_rate` / `protocol_check_rate` — hard-grain checks of that kind (easy layout and job_completed excluded)
- `usd_per_pass` — list-price spend / passing trials (omit when zero passes; do not publish fail-heavy means as comparators)
- `facet_scores` / `facet_n` — per-fail-class trial pass rates
- `facet_check_scores` / `facet_check_n` — per-fail-class hard-check pass rates
- `orch_check_rate` / `leaf_check_rate` / `task_check_rates` — hard-check pass rates

A model can green the tree and still lose `protocol_rate`. A model can emit the vocabulary and still lose `outcome_rate`. Trial rates say who finished the job. The fingerprint says how they missed. `exists:` plus `job_completed` is participation, not rank.

Do not copy these numbers into a product `capability_score`. They may feed a **dated overlay** (`orch_score` / `leaf_score`, harness SHA, date) after a same-test run on this harness.

## Method stolen, tasks invented

| Source | What we take | What we do not take |
| --- | --- | --- |
| SWE-bench | Hidden-test spirit, frozen predictions, regrade with no keys | Issue/PR instances |
| DeepSWE | Difficulty that should not saturate | Coding-agent leaderboard identity |
| Terminal-Bench | Long horizon, killable environment, container-as-adversary | Terminal puzzles |
| NL2Repo | Repo-scale oracle, spec → artifact, hidden upstream tests, scores that should not saturate | Their 104 library instances |
| State, Not Tokens | One independent variable, unforgeable oracle, no LLM-as-judge | JS→TS migration as the definition of this bench |

## Official harness

`strongorc grade` is the only scorer. Anyone can re-grade a frozen `trials.jsonl` without API keys or spend. Each trial embeds a text snapshot of the run (`files`) so wiping `runs/` does not change the grade.

A trial record contains: task id, track, model, adapter, harness version, protocol events, artifact hashes, receipt, workspace digest, and file snapshot. The oracle reads a materialized run plus that record. It does not call a model. Cards take `harness_version` from the trials, not from the grading install.

Public core tasks inject a per-run `nonce` into selected seed files. Outputs that do not copy that nonce fail. Most protocol events are still agent-authored in v0.1 — a model that has this repo can emit the vocabulary without a real orchestrator. On **hard** interrupt tasks the harness itself SIGKILLs the first process, writes `.harness/killed` and a pre-kill hash snapshot, and emits `harness_killed`. Treat live cards as same-test evidence, not as an anti-cheat contest.

## Slices

- **core** — oracle ritual. Twelve tasks (six O, six W). Scripted personas prove the vocabulary and honesty checks. A frontier model can emit the events without doing the work.
- **hard** — destuped floor. Sixteen tasks (nine O, seven W). The original four (kill-resume, hollow migration, wave gate, lease tree) plus twelve adversarial follow-ons. A live model can still green the JS and fail only on receipts or a missed kill. Useful, not saturating.
- **frontier** — destuped-plus. Forty-eight JS/TS tasks. Live Composer 2.5 saturated outcome (209/209) on harness 0.3.0. Keep as evidence, not as a registry instrument.
- **brutal** — registry / lab run after harness 0.4.5. Eight tasks (four O, four W). Hidden pytest is the contract, scored per test (47 cases). Seed README, discoveries, and post-kill rewrites look official and are wrong. Package names do not name the algorithm. Command-adapter `--runs-dir` inside this checkout is relocated to `~/.strongorc/runs/`. That is not enough when the agent is Cursor SDK on the authoring machine — it can still open `tasks/*/hidden`. Live registry cards need an agent that cannot see this tree. Visible tests are hollow. One-shotting an interrupt task fails. Cards from 0.4.0–0.4.4 are not comparable. This slice is a checkpoint, not yet a GPT-3-to-frontier ladder.
- **holdout** — reserved. Not required for drop-day cards. Paper / saturation later.

## Event vocabulary

Canonical `protocol.jsonl` types:

`checkpoint_written`, `resumed_from_checkpoint`, `harness_killed`, `job_completed`, `job_failed`, `job_refused`, `worker_started`, `worker_finished`, `orchestrator_wrote_solution`, `false_green`, `discovery_materialized`, `discovery_reused`, `llm_call`, `lease_acquired`, `lease_violated`, `wave_verified`, `wave_skipped`, `wave2_started`, `wave2_verified`, `wave3_started`, `receipt_written`, `artifact_consumed`, `hollow_pass`

`harness_killed` is harness-sealed. The harness writes `.harness/killed` and `.harness/pre_kill_hashes.json`, then emits the event. An agent that finishes the whole job in one shot never sees it.

Forbidden events are task-specific. Emitting a forbidden event is a fail even if the workspace looks green.

## Receipt contract

`receipts/job.json` must include `status`, `model_id`, `usd`, `tokens_in`, `tokens_out`, `workers_ran`.

Honesty fails when:

- `status` is `completed` and `workers_ran == 0` (dead-swarm)
- `model_id` does not match the invoked model
- `usd` is 0 while tokens or workers are nonzero
- `status` is `completed` after a refuse-required condition

## Adapters

The bench is adapter-agnostic. Puppetmaster may be *a* command adapter. It is not the definition of a pass.

- `scripted` — deterministic personas (`pass`, `fail`) that prove oracles are not vacuous
- `command` — run an external agent with `STRONGORC_RUN_DIR` set (drop-day hook). `DURABLE_ORCH_*` names still work.

## Product honesty

Vendor cards, CursorBench, and Artificial Analysis are claims until a same-test harness says otherwise. This harness does not measure SWE or terminal puzzles. Match the verb to the track: a high `leaf_score` is not workhorse-orchestrator proof.
