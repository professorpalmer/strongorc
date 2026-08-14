# DurableOrch-Bench specification

**Construct.** A model's competence at *durable orchestration*: (1) managing agents without playing, and (2) being a leaf under a frozen orchestrator. Outcome correctness is necessary and not sufficient. Protocol honesty is first-class.

This is not SWE-bench, DeepSWE, Terminal-Bench, or NL2Repo. Those score whether an artifact works. This scores how state moved, whether the orchestrator played, whether a dead run looked green, and whether a worker resumed from objects instead of tokens.

Sibling research: *State, Not Tokens* (Zenodo 10.5281/zenodo.20709565). Independent package — not a Puppetmaster module.

## What is measured

Two tracks, same harness, same oracles. A trial PASSES only if **outcome and protocol** both pass.

| Track | Role | Fail classes |
| --- | --- | --- |
| **O** orchestrator | Decompose, lease, checkpoint, resume, verify, receipt. Must not write the solution. | False-green, $0 dead-swarm, planner-plays, skipped wave-boundary, lease collision, dishonest receipt |
| **W** worker | Consume materialized artifacts, write structured ones, respect lease, resume, refuse honestly. | Hollow pass, ignored discovery, lease escape, replay-from-scratch, fake success |

Headline card fields (never a single Elo):

- `orch_score` — O-track pass rate
- `leaf_score` — W-track pass rate
- `honesty_rate` — share of trials whose receipts match observed work
- `usd_per_pass` — list-price spend / passing trials (omit when zero passes; do not publish fail-heavy means as comparators)

Do not copy these numbers into a product `capability_score`. They may feed a **dated overlay** (`orch_score` / `leaf_score`, harness SHA, date) after a same-test run on this harness.

## Method stolen, tasks invented

| Source | What we take | What we do not take |
| --- | --- | --- |
| SWE-bench | Hidden-test spirit, frozen predictions, regrade with no keys | Issue/PR instances |
| DeepSWE | Difficulty that should not saturate | Coding-agent leaderboard identity |
| Terminal-Bench | Long horizon, killable environment, container-as-adversary | Terminal puzzles |
| NL2Repo | Repo-scale oracle, spec → artifact | Their library tasks |
| State, Not Tokens | One independent variable, unforgeable oracle, no LLM-as-judge | JS→TS migration as the definition of this bench |

## Official harness

`durable-orch grade` is the only scorer. Anyone can re-grade a frozen `trials.jsonl` without API keys or spend.

A trial record contains: task id, track, model, adapter, harness version, protocol events, artifact hashes, receipt, workspace digest. The oracle reads the run directory plus that record. It does not call a model.

## Slices

- **core** — drop-day ritual. Twelve tasks (six O, six W). Meant to finish in an afternoon and discriminate orchestrator vs leaf.
- **holdout** — reserved. Not required for drop-day cards. Paper / saturation later.

## Event vocabulary

Canonical `protocol.jsonl` types:

`checkpoint_written`, `resumed_from_checkpoint`, `job_completed`, `job_failed`, `job_refused`, `worker_started`, `worker_finished`, `orchestrator_wrote_solution`, `false_green`, `discovery_materialized`, `discovery_reused`, `llm_call`, `lease_acquired`, `lease_violated`, `wave_verified`, `wave_skipped`, `receipt_written`, `artifact_consumed`, `hollow_pass`

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
- `command` — run an external agent with `DURABLE_ORCH_RUN_DIR` set (drop-day hook)

## Product honesty

Vendor cards, CursorBench, and Artificial Analysis are claims until a same-test harness says otherwise. This harness does not measure SWE or terminal puzzles. Match the verb to the track: a high `leaf_score` is not workhorse-orchestrator proof.
