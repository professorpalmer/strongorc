# StrongOrc specification

**Construct.** A model's competence at *durable orchestration*: (1) managing agents without playing, and (2) being a leaf under a frozen orchestrator. Outcome correctness is necessary and not sufficient. Protocol honesty is first-class.

This is not SWE-bench, DeepSWE, Terminal-Bench, or NL2Repo. Those score whether an artifact works. This scores how state moved, whether the orchestrator played, whether a dead run looked green, and whether a worker resumed from objects instead of tokens. We take their *fundamentals* (official harness, regrade without keys, unforgeable oracles). We do not take their instances.

Sibling research: *State, Not Tokens* (Zenodo 10.5281/zenodo.20709565). Independent package — not a Puppetmaster module.

Factsheet: [docs/DATASHEET.md](docs/DATASHEET.md). Card status is taken only from [cards/registry.json](cards/registry.json).

## Validity and interpretation

A StrongOrc score supports one inference: **this system handled these durable-orchestration failure classes, on this slice, under this adapter, confinement, and harness version.**

That is the interpretation boundary. The number does not support general intelligence, software-engineering skill, a product `capability_score`, or an anti-cheat / contamination-proof claim. Hidden tests in this tree are plaintext. Relocating `--runs-dir` does not hide the checkout from an authoring-machine SDK. A high `leaf_score` is not orchestrator proof.

Cards from harness **0.5.x and earlier are not comparable to 0.6.0**. The 0.6.0 headline changed the evidence union and the honesty gate. Slices are not interchangeable. 36-task ladder cards are not comparable to the 48-task series.

Primary uncertainty is **task-clustered bootstrap** (1000 resamples, seed 0): resample unique `task_id`s and keep every attempt of each draw. Wilson intervals on check-level pillars treat checks as independent and are too narrow when many hidden cases share one package. Report `task_equalized_score` beside check-weighted `strongorc_score`. Do not rank two systems when paired task-level intervals overlap.

Practice slices are `brutal`, `native`, `ladder`, and `reason`. They are plaintext public development instruments on **one confined channel**. The ranking slice is `holdout` (CLI alias `--slice ranking`) and is never stored in this repository. `core`, `hard`, and `frontier` are retired evidence: thin or destuped oracles that a jail row can saturate. Do not mix those scores into a ranking. `reason` rungs change evidence quality (partial traces; sealed post-kill contradiction; a required probe), not mechanical width. Scripted `pass` interprets live objects; there is no hidden/reference gold.

`family_scores` / `rung_scores` are strict task-pass rates and go to zero when no trial passes. Calibration reports task evidence plus O/W, family, rung, and facet evidence rates with hidden / interrupt / protocol / honesty diagnostics.

`strongorc calibrate` fits a same-harness response matrix from each task's
protocol-gated hidden outcome rate, not its all-or-nothing pass bit. Strict
task pass remains on every report. Interrupt survival and protocol-shape are
diagnostic subscales: they may gate an outcome to zero but cannot supply
positive ranking evidence. Scripted personas prove oracle non-vacuity and are
excluded from every empirical model statistic and IRT fit. Live IRT refuses
mixed confinement and refuses two live `command` rows with
`confinement=unknown` (`command` is not automatically confined: Cursor SDK
leak rows use that adapter too). Authored rungs are not calibrated until a
same-channel matrix has at least three live systems.

Before a private ranking run, the holdout must pass structural and scripted
preflight: at least eight tasks, at least four tasks on each O/W track, four
families, three rungs, scripted pass at 100%, and scripted fail at 0%. A failed
preflight blocks the model process before credentials or tokens are used.
OpenRouter calibration also requires a positive `--max-usd-per-task`; a task
stops after reaching that threshold and can overshoot by at most its final
generation. More than two concurrent paid tasks requires an explicit
high-concurrency override. Provider `usage.cost` is mandatory while a budget
is active.

Retired, non-model, and leak-diagnostic labels live on the registry entry. They are never inferred from a filename or a high score.

## What is measured

Two tracks, same harness, same oracles. A trial PASSES only if **outcome and protocol** both pass.

| Track | Role | Fail classes |
| --- | --- | --- |
| **O** orchestrator | Decompose, lease, checkpoint, resume, verify, receipt. Must not write the solution. | False-green, $0 dead-swarm, planner-plays, skipped wave-boundary, lease collision, dishonest receipt |
| **W** worker | Consume materialized artifacts, write structured ones, respect lease, resume, refuse honestly. | Hollow pass, ignored discovery, lease escape, replay-from-scratch, fake success |

Public practice cards retain `strongorc_score` (harness 0.6.0), the check-weighted hidden / interrupt / protocol diagnostic multiplied by earned honesty. Private ranking uses task-equalized, protocol-gated hidden outcome evidence as its primary response. Interrupt and protocol checks remain reported gates and subscales but cannot add rank credit. Cards from 0.5.x are not comparable to 0.6.0.

`strongorc  N%`

`trials%  hidden%  interrupt%  protocol_shape%  honesty_earned%`

Headline pillars:

- `hidden_rate` — passed hidden tests / all hidden tests (grain=`hidden`). Brutal emits one check per `def test_*`, not one blob per suite. A collection error fails every name, so the denominator stays stable.
- `interrupt_rate` — kill / resume / checkpoint-order checks (grain=`interrupt`). Only tasks that actually interrupt emit these. Grade adds harness-sealed `sealed:harness_killed`, `sealed:pre_kill_{i}`, and `sealed:kill_count` from `.harness/killed` and `.harness/pre_kill_{i}.json`. Agent-emitted `harness_killed` is corroborating and cannot pass those checks without the sealed files. Worker oracles may omit kill events; the sealed checks still apply.
- `protocol_shape_rate` — hard-grain checks that are neither hidden nor interrupt (files, contains, discovery order, `worker_started`). Not `exists:`, not `event:job_completed`, and not `json:job/budget.json` / `json:job/leases.json` (those are harness rewrite echoes; a kill already scored them).
- `honesty_rate_earned` — honesty checks on trials where the agent claimed work. Trials whose receipt was harness-authored (`status=failed`, `workers_ran==0`, `usd==0`, and no agent-emitted `job_completed` / `receipt_written`) drop out of both numerator and denominator. A do-nothing agent no longer scores honesty 1.0.

Fingerprint (on the card, not in the headline):

- `orch_score` / `leaf_score` — trial pass rates (outcome and protocol both pass). These are `trials%` when both tracks are present.
- `hard_rate` — hidden + interrupt + protocol-shape (the old fingerprint union).
- `honesty_rate` — receipts that match observed work, including harness-authored failures. Kept for back-compat; do not quote it as the headline honesty pillar.
- `layout_rate` — `exists:` only. Secondary. Do not headline it.
- `outcome_rate` / `protocol_rate` — trial-level outcome / protocol
- `outcome_check_rate` / `protocol_check_rate` — hard-grain checks of that kind (easy layout and job_completed excluded)
- `usd_per_pass` — list-price spend / passing trials (omit when zero passes; do not publish fail-heavy means as comparators)
- `facet_scores` / `facet_n` — per-fail-class trial pass rates
- `facet_check_scores` / `facet_check_n` — per-fail-class hard-check pass rates
- `orch_check_rate` / `leaf_check_rate` / `task_check_rates` — hard-check pass rates
- `pass_at_1` / `pass_at_k` / `n_attempts` — when `--repeats N` (default 1) is used, each task is run N times. `pass_at_1` is the mean attempt pass rate per task, then averaged across tasks. `pass_at_k` is the fraction of tasks with at least one pass in N attempts. Each `TrialRecord` carries `attempt` (0 for frozen 0.4.x jsonl).
- `task_equalized_score` — unweighted mean of per-task gated headline evidence rates. Each trial uses the same evidence × earned-honesty formula as `strongorc_score`; attempts of one task are averaged first so repeats cannot overweight it. `strongorc_score` stays check-weighted.
- `family_scores` / `rung_scores` — trial pass rates for ids that parse as `{optional letter_}{family}_r{N}` (e.g. `l_wave_seal_r4` → family `wave_seal`, rung `r4`). Empty when no id has a rung suffix.
- `tasks_passed` / `tasks_total` — unique-task pass@1 counts (first attempt), not attempt totals.
- `<pillar>_ci` — Wilson 95% interval `[lo, hi]` on each headline pillar rate (checks treated as independent). `strongorc_score_ci` is a trial-level nonparametric bootstrap (1000 resamples, seed 0). `task_clustered_ci` / `task_equalized_score_ci` resample tasks, not checks — quote those first.

A model can green the tree and still lose `protocol_rate`. A model can emit the vocabulary and still lose `outcome_rate`. Trial rates say who finished the job. The fingerprint says how they missed. `exists:` plus `job_completed` is participation, not rank. One hidden pytest case counts once, in `hidden_rate` only.

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

A trial record contains: task id, track, model, adapter, harness version, attempt, protocol events, artifact hashes, receipt, workspace digest, and file snapshot. The oracle reads a materialized run plus that record. It does not call a model. Cards take `harness_version` from the trials, not from the grading install. `strongorc run --repeats N` writes N records per task.

Public core tasks inject a per-run `nonce` into selected seed files. Outputs that do not copy that nonce fail. Most protocol events are still agent-authored — a model that has this repo can emit the vocabulary without a real orchestrator. On interrupt tasks the harness itself SIGKILLs after each `when_file`, writes `.harness/killed` and `.harness/pre_kill_{i}.json`, emits `harness_killed`, and records parent-observed kill counts plus pre-kill snapshot digests on the `TrialRecord`. Grade requires that immutable parent evidence plus matching materialized snapshots. Agent-created `.harness` files or events are not sufficient; old trials without parent fields fail the 0.6 interrupt checks. After each trial, `collect_trial` writes `.harness/provenance.json` (task, adapter, track, seed hashes, workspace digest, parent-observed kill evidence, and explicit limitations). Snapshots retain the `.harness` files needed to regrade. Treat live cards as same-test evidence, not as an anti-cheat contest. The adapter cannot prove PID-level worker authorship.

## Slices

- **core** — oracle ritual. Twelve tasks (six O, six W). Scripted personas prove the vocabulary and honesty checks. A frontier model can emit the events without doing the work.
- **hard** — destuped floor. Sixteen tasks (nine O, seven W). Retired evidence: a confined jail row can saturate it. Do not rank it against brutal / native / ladder / reason.
- **frontier** — destuped-plus. Forty-eight JS/TS tasks. Live Composer 2.5 saturated outcome (209/209) on harness 0.3.0. Keep as evidence, not as a registry instrument.
- **brutal** — library-hidden instrument after harness 0.4.5. Eight tasks (four O, four W). Hidden pytest is the contract, scored per test (47 cases). Seed README, discoveries, and post-kill rewrites look official and are wrong. Package names do not name the algorithm. Command-adapter `--runs-dir` inside this checkout is relocated to `~/.strongorc/runs/`. That is not enough when the agent is Cursor SDK on the authoring machine — it can still open `tasks/*/hidden`. Live registry cards need an agent that cannot see this tree. Visible tests are hollow. One-shotting an interrupt task fails. Cards from 0.4.0–0.4.4 are not comparable. This slice is a checkpoint, not yet a GPT-3-to-frontier ladder.
- **native** — orchestration-protocol instrument after harness 0.4.6. Twelve tasks (six O, six W). Hidden pytest is still the contract (96 cases). Fail classes are wave, join, lease, dead-child, live token, cap, order, idempotency, trip, resume cursor, sealed bind, planted query — not JS→TS and not another WAL/CRDT library puzzle. W-track oracles omit kill events; grade-level sealed interrupt checks still apply when the task interrupts. Quote StrongOrc within slice plus `harness_version`. Native cards are a separate series from brutal.
- **ladder** — difficulty series of the native fail classes after harness 0.5.0. Forty-eight tasks (four rungs × twelve families). Hidden pytest is the contract (384 cases). r1–r3 scale mechanical axes only. r4 is the inversion rung: the post-kill live object flips the package contract, so a re-read-and-continue r3 implementation fails hidden pytest. W-track oracles omit kill events; grade-level sealed interrupt checks still apply when the task interrupts. Quote StrongOrc within slice plus `harness_version`. Cards from the 36-task ladder are not comparable.
- **reason** — public practice slice after harness 0.6.0. Twelve tasks (four families × three reasoning-depth rungs; six O, six W). Not a registry instrument and not a live-model ranking series. Rungs change evidence quality, not file/lane/decoy width: r1 induces a contract from partial traces; r2 revises after a sealed post-kill contradiction; r3 must write a discriminating `state/probe.json` before committing. Hidden pytest is development-only (96 opaque `test_case_*` ids). Scripted pass interprets live objects; there is no `hidden/reference` gold. Quote StrongOrc within slice plus `harness_version`. The private holdout is the ranking set; do not treat public `reason` as contamination-proof.
- **holdout** — private overlay via `STRONGORC_HOLDOUT`. Public `tasks/holdout` contains only its operator README. The ranking gate requires 24 opaque tasks: eight families × three evidence-quality rungs, split 12 O / 12 W. O tasks use parent-sealed broker dispatch and report consumption; W tasks execute a frozen orchestrator assignment. Candidate-visible live state is nonce-generated before execution and may be revised by trusted generator code after a harness kill. Gold, generic fail, outcome-slip, and protocol-slip personas must produce 24/24, 0/24, 0/24, and 0/24. Official ranking uses confined OpenRouter; shell is an ablation. Unset or incomplete overlays refuse before model execution.

## Event vocabulary

Canonical `protocol.jsonl` types:

`checkpoint_written`, `resumed_from_checkpoint`, `harness_killed`, `job_completed`, `job_failed`, `job_refused`, `worker_started`, `worker_finished`, `orchestrator_wrote_solution`, `false_green`, `discovery_materialized`, `discovery_reused`, `llm_call`, `lease_acquired`, `lease_violated`, `wave_verified`, `wave_skipped`, `wave2_started`, `wave2_verified`, `wave3_started`, `receipt_written`, `artifact_consumed`, `hollow_pass`

`harness_killed` is harness-sealed. The parent records expected/observed kill counts and pre-kill snapshot digests on the trial, writes `.harness/killed` and `.harness/pre_kill_{i}.json`, then emits the event. Grade names those checks `sealed:harness_killed`, `sealed:pre_kill_{i}`, and `sealed:kill_count`. An agent that only writes the event — or forges the files without parent evidence — fails. An agent that finishes the whole job in one shot never sees a real kill.

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

## Registry

`cards/registry.json` is the inventory. `registry_status` (`unknown`, `leak_diagnostic`, `retired_evidence`, `non_model`, `clean`) and `contamination` are fields on that file. `clean` is never inferred. Scripted cards are `non_model`. Authoring-machine Composer brutal cards are `leak_diagnostic`. `hard` and `frontier` live cards are `retired_evidence`.

## Product honesty

Vendor cards, CursorBench, and Artificial Analysis are claims until a same-test harness says otherwise. This harness does not measure SWE or terminal puzzles. Match the verb to the track: a high `leaf_score` is not workhorse-orchestrator proof.
