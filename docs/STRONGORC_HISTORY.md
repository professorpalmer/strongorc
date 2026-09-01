# StrongOrc development record

This document is the durable chronology of StrongOrc design decisions,
experiments, failures, and reversals. It is evidence for the accompanying
benchmark-construction retrospective, not a leaderboard.

Every reported result must be qualified by slice, harness version, and
evaluation channel. Results from different slices or harness versions are not
directly comparable. Cursor SDK runs from the authoring machine are leakage
diagnostics because that agent can read `tasks/*/hidden`.

## Source sessions

The local Cursor history was reconstructed from these parent conversations:

- `d0f7072b-5dbd-4b69-9ca6-e57c2ac877c6` is the founding empty-window
  session.
- `339c6021-8d3f-428c-beab-8b1d427117ca` continues that founding session after
  the workspace move.
- `15adafb8-bc39-4290-a557-129674dd5d76` contains the frontier, brutal, and
  scoring 0.4.x work.
- `0950fd8b-b1ac-49ca-921b-a87e0c218f04` and
  `df725e15-90ba-4a4a-9162-ea41b52068f5` are the same relocation request,
  before and after moving into this workspace.
- `287227ab-8002-45d7-84ef-cb3610c7c99d` contains scoring 0.5.0, native,
  ladder, r4 inversion, and the live Grok ceiling probe.
- `34b3f9af-8ae0-4cb0-9e3c-22b024d7ffc8` is the 2026-08-28–29 confined
  OpenRouter wave (Kimi, Sol, Fable) and the jail-ablation decision.

Puppetmaster worker transcripts are supporting work products, not additional
user sessions. An exhaustive local search found no additional independent
StrongOrc design conversation under `/Users/carypalmer`.

One additional parent conversation,
`c1381f45-66d5-4b35-bfb8-6ebe57265032` (“Grok Bot frontend strategies”),
later asked to harvest StrongOrc and other project transcripts into the wiki.
It is provenance for the wiki distillation, not a seventh benchmark-design
session.

The same six sessions also appear as smaller stale `empty-window` copies after
workspace moves. Harness-run workspaces contain hundreds of evaluated-agent
transcripts, but no additional user design conversations. The only
off-transcript StrongOrc archive found locally is
`my-portable-llm-wiki/raw/conversations/2026-08-14-strongorc-ship.md`, which
summarizes the founding session rather than adding a new one.

## Chronology

### 2026-08-14: define the construct

The founding requirement was a benchmark for two distinct capabilities:

1. An orchestrator manages workers without doing their work.
2. A worker consumes durable objects correctly under a frozen orchestrator.

The benchmark was deliberately made a sibling of State, Not Tokens rather than
a Puppetmaster module. It borrowed evaluation methods from SWE-bench,
DeepSWE, Terminal-Bench, and NL2Repo but invented its own instances.

The first `core` slice contained 12 protocol tasks. It established the official
harness, run nonces, snapshot regrading, and scripted pass/fail personas.
It quickly proved too weak. The `hard` slice added live SIGKILL and resume.
A relative `--runs-dir` bug initially placed checkpoints one directory too
deep, causing resume tests to hang until their timeout.

### 2026-08-15: discover saturation

GLM-5.3 passed the four-task hard floor 4/4. The hard series grew to 12 and then
16 de-duplicated tasks. Composer 2.5 passed 11/16 while GLM-5.3 passed 8/16,
but both nearly saturated outcome checks.

The `frontier` slice expanded to 48 JS-to-TS tasks. Composer 2.5 passed all
209 outcome checks and missed only three protocol kills. This was the first
clear lesson that adding more versions of the same task did not create a
frontier benchmark.

The response was `brutal`: eight package tasks with hidden pytest oracles,
borrowing NL2Repo's evaluation method. Early Composer results exposed three
different validity failures:

- Seed files and API names leaked the intended algorithm.
- Integrity hashing included disposable `.venv` and `__pycache__` files,
  creating false failures after snapshot materialization.
- Cursor SDK on the authoring machine read hidden tests and reference packages.

The contaminated Composer cards remain useful only as leakage diagnostics.

### 2026-08-16: scoring decontamination

Confined OpenRouter runs of Gemini 3.7 Flash and GPT-4o both failed all eight
brutal trials and all 47 hidden tests. Their different partial behavior exposed
problems in the score rather than establishing a useful model ranking.

Scoring changed repeatedly:

- 0.2.0 separated outcome and protocol rates.
- 0.3.0 added facet fingerprints.
- 0.4.3 counted every hidden `test_*` separately, moved existence and
  `job_completed` checks out of the hard fingerprint, and stopped requiring
  `harness_killed` on worker tasks that did not interrupt.
- 0.4.4 sealed harness-written budget and lease files so post-kill rewrites did
  not inflate model skill.
- 0.4.5 introduced a public `strongorc_score` as an unweighted mean of card
  rates. That formula later proved to mix participation with capability.

The published repository stopped at this 0.4.5 checkpoint. Native
orchestration families were started but paused.

### 2026-08-19–20: scoring v2 and the ladder ceiling

Scoring 0.5.0 replaced the unweighted mean with a single-counted,
check-weighted union of hidden, interrupt, and protocol-shape evidence,
multiplied by earned honesty as a gate. Harness-authored do-nothing failures no
longer receive an honesty bonus. Wilson pillar intervals, a trial bootstrap,
repeats, and pass-at-k were added.

The `native` slice introduced 12 orchestration-specific fail classes. The
`ladder` repeated those families at r1–r3 while scaling mechanical dimensions
such as lane count, join width, decoy count, and kill count.

Grok 4.6 Extra High cleared the 36-task ladder 36/36 on the authoring machine.
The r4 ceiling then inverted each live contract after kill. Grok 4.6 Extra
High + Fast passed 47/48 and scored 0.985 on the 48-task version; the only miss,
`l_slate_r1`, failed before producing a package while r2–r4 passed. All r4
inversions passed.

This result is not a registry card:

- The Cursor agent could read the checkout's hidden tests and references.
- r1–r3 scale width, not reasoning depth.
- r4 is a single “re-read the live object” inversion heuristic repeated across
  12 families.
- Hidden pytest contributes 384 of the 551 headline checks.
- Missing one task's eight hidden tests yields `(376 + 96 + 71) / 551 = 0.985`.

The result therefore demonstrates saturation and score granularity, not
frontier orchestration ability.

## Lessons earned

1. Define the construct before the task format.
2. Borrow evaluation methods, not benchmark instances.
3. A pass requires both outcome and protocol.
4. Scripted pass and fail personas test oracle non-vacuity; they are not model
   results.
5. Easy existence checks and harness-authored state measure participation, not
   capability.
6. Binary trial pass rates hide useful failure grain, but check-weighting can
   also let verbose task families dominate.
7. Hidden tests are not hidden from an agent that can read the checkout.
   Confinement is part of the measurement.
8. More files, kills, lanes, or decoys do not necessarily increase reasoning
   difficulty.
9. Saturation should retire or redesign an instrument, not produce a victory
   headline.
10. Every number needs slice, harness version, adapter, confinement status,
    attempts, and uncertainty.
11. Do not copy StrongOrc scores into a product `capability_score`.
12. A public static benchmark needs a private, rotating successor before it
    becomes training data.
13. A same-jail column of task-pass zeros is a filter, not a ranking of
    the field. Ease the jail before easing the oracles.

### 2026-08-20: calibration instrument

After the 0.6.0 validity overhaul, calibration was implemented as a
same-harness response matrix plus optional 2PL, not another mechanical
rung. `strongorc calibrate` fits frozen jsonl; `scripts/calibrate.py`
runs scripted personas and optional confined OpenRouter rows.
`cards/preregister/reason-0.6.0.json` locks the live protocol (three
attempts, two systems per band, command adapter). Scripted pass/fail on
`reason` is oracle non-vacuity (12/12 pass, 0/12 fail, IRT unidentified).
A same-channel weak/mid/frontier matrix is still required before any item
is called calibrated. Live rows first used Cursor plan credits through
`examples/cursor_agent.py` (isolated run dirs, `authoring_sdk` /
`leak_diagnostic`). The OpenRouter cash wave was stopped.

### 2026-08-21: Cursor leak-diagnostic reason wave

Same public `reason` slice, Cursor SDK, authoring machine:

- `grok-4.6` Extra High + Fast: 11/12 tasks. Only miss
  `r_split_reports_r3`. Task-equalized ~0.92. Above the 0.80–0.90
  rewrite line even if treated as a peek.
- `composer-2.5`: 8/12. Swept `retract_rule` and `trace_contract`.
  Missed the `diagnose_kill` family and `r_split_reports_r1`. Oracles
  are not vacuous.
- `gpt-5.4-nano`: crashed. `read_events` `JSONDecodeError` on a smashed
  `protocol.jsonl` line. Partial in-place grade about 1/10.

Public `reason` is too close to “read traces and implement.” Next
instrument work is harder underdetermination and a private holdout, not
r5 width. The confined follow-up channel is Puppetmaster CLI `agentic`
pinned through OpenCode Go (`examples/agentic_opencode_agent.py`,
`cards/preregister/reason-0.6.0-opencode-go.json`): `ox-alpha-free` and
`minimax-m2.5`. Do not mix those rows with the Cursor SDK series.

### 2026-08-22: ranking-80 and the confined jail

Owner-resolved: the live ranking instrument is 80 tasks (brutal 8 +
native 12 + ladder 48 + reason 12). Core / hard / frontier stay retired
evidence. Reason is a ranking slice. Cursor SDK on a machine that has
this clone is not a jail. The clean live path is
`examples/openrouter_agent.py` (tools locked to `$STRONGORC_RUN_DIR`, no
shell). IRT refuses mixed channels. Do not destup ranking oracles “up to
reason.” Do not author holdout in this checkout.

Two confined floors (`stealth/ox-alpha`, `google/gemini-3.7-flash`)
finished hidden 0 on every ranking slice. That is underpowered, not a
published `strongorc_score`. An 80-wide `anthropic/claude-opus-5` launch
at `--jobs` = task count was killed in minutes (OpenRouter in-flight
reserve, no jsonl). Slice jsonl writes only after the whole slice.
Spend protocol after that: probe `reason` first, never 80-wide on
Opus-class models.

### 2026-08-28–29: five-system confined floor

Same OpenRouter jail, same 80, provider-default reasoning (no
High/Max/Low knob), one attempt. Five systems, zero ranking-task
passes. Headlines are interrupt plus a bit of protocol-shape. Hidden
stays ~0. IRT remains unidentified because the pass matrix is all
zeros.

Weighted 80 (check-weighted `strongorc_score` × honesty gate; not a
leaderboard):

| System | Score | Hidden | Interrupt | Passed |
| --- | ---: | ---: | ---: | ---: |
| `anthropic/claude-fable-5` | 11.3% | 0.16% | 38% | 0/80 |
| `openai/gpt-5.6-sol` | 9.8% | 0 | 36% | 0/80 |
| `moonshotai/kimi-k3` | 9.3% | 0.16% | 33% | 0/80 |
| `stealth/ox-alpha` | 6.9% | 0 | 23% | 0/80 |
| `google/gemini-3.7-flash` | 4.4% | 0 | 16% | 0/80 |

Fable’s only hidden crumb is reason **1.04%**. Kings are better at the
easy grain (checkpoint, eat SIGKILL, resume). They still do not ship
the oracle-visible outcome. They also waste wall clock calling `wait`
on rungs that never kill.

Five confined zeros cannot tell “the 80 are too hard” from “this jail
is the wall.” Destup is not licensed from this matrix. First walk-down
is affordance: same king, add `run_command` in the run dir, new dest,
do not `--fit` with confined jsonl. Compare **hidden**, not the
headline.

Lab dest: `~/.strongorc/calibration/<slice>/openrouter/`. Harness stays
0.6.0. Published git tip is still `15067f2`. Ranking-80 and calibrate
live in the dirty `dev` tree.

### 2026-08-29: jail ablation in flight

Channel `openrouter-shell` (`examples/openrouter_agent.py --allow-shell`).
Confinement stamp `unconfined`. `run_command` cwd is the run dir; HOME
is remapped; commands that name the checkout path are refused. This is
not Cursor SDK and not a hidden-test leak.

Live cell: Fable on `reason` only, `--jobs 2`. Dest
`~/.strongorc/calibration/reason/openrouter-shell/`. Started 03:08 CDT.
If hidden moves or a task passes, the 80 were passable and the confined
tool box was the clamp. If hidden stays ~0, destup of hidden is
licensed, one constraint at a time, old column kept as retired
evidence.

### 2026-08-29: public face is practice; ranking is holdout

`--slice ranking` is no longer the public 80. Practice slices are
brutal / native / ladder / reason (`--slice practice` for a dev sweep).
The ranking alias expands to `holdout` and fail-closes without
`STRONGORC_HOLDOUT`. The confined ranking-80 matrix and destuped reason
cells stay lab evidence. Do not quote public reason as a registry rank.

### 2026-08-29: retired one-track bank was a 12-task overlay

The first testable ranking set is 4 families × 3 rungs minted outside
git (`~/.strongorc/holdout`) via `scripts/mint_holdout.py`. Families
are relay / freeze / ledger / assay — destuped consume/dispatch verbs,
sealed interrupt on freeze, hash-mismatch raise kept as construct on
assay r3. Public `tasks/holdout` holds opaque stubs only.

At that point, the intended live channel was `openrouter-shell`.
Practice stays confined. Incremental jsonl after each task. Grain
rates (hidden / interrupt / protocol / honesty) plus `usd_per_task`
are the close-model scoreboard when task-pass is still a floor.

### 2026-08-29: quarantine the one-track holdout and stop paid guessing

The first private bank was not a valid StrongOrc ranking instrument:
all 12 relay / freeze / ledger / assay tasks were orchestrator tasks.
It could not measure the second half of the construct, being
orchestrated. The first prompt version also hid the package surface and
produced a Fable 0/12 crypto-guess wall. Named-surface v2 disproved that
floor: the completed smoke passed, and offline regrade of the aborted
wave recovered 3 passes from 9 recorded trials. No rerun was needed.

The repair keeps private holdout as the eventual ranking shape but
fail-closes it until it has at least four tasks per O/W track, four
families, three rungs, scripted pass 100%, and scripted fail 0%.
`--slice ranking --validate-only` now reports the current missing worker
track. Public `reason` passes its zero-cost scripted preflight (12/12
pass, 0/12 fail) and remains the calibration instrument.

Calibration v3 uses each task's gated hidden / interrupt /
protocol-shape evidence rate as the empirical response while retaining
strict task pass. Scripted personas are excluded from empirical curves
and IRT. This removes the all-zero response-matrix artifact without
weakening the task pass contract.

OpenRouter live calibration now requires an explicit positive
`--max-usd-per-task`. The agent accumulates provider `usage.cost`,
persists it across resume, refreshes receipts after the final turn, and
stops when the threshold is reached (with at most the final generation's
overshoot). Missing provider cost fails closed.
Paid concurrency defaults to two; larger waves require an explicit
override.

### 2026-08-29: frontier-v2 private bank reaches live-calibration readiness

The one-track overlay was retired rather than repaired in place. A fresh
off-git bank now has 24 opaque tasks: eight independent families × three
evidence-quality rungs, split 12 orchestrator / 12 worker. No task metadata,
id mapping, gold agent, fail persona, generator, worker pool, or oracle is
checked into the repository.

The harness now materializes nonce-bound candidate-visible state before
execution and trusted post-kill state after a parent-observed interrupt.
Orchestrator tasks use a parent-owned local worker broker. Its dispatch and
report-consumption records are frozen into the trial, so agent-authored
protocol events and receipt counts cannot forge delegation. Worker tasks
receive a frozen orchestrator assignment.

The calibration response was narrowed from mixed positive evidence to
protocol-gated hidden outcome evidence. Interrupt survival, protocol shape,
and honesty are still reported, but they can only invalidate outcome credit.
Track-specific O/W evidence plus family, rung, and facet rates provide
diagnostic separation. Repeated attempts now have unique run directories and
merge by `(task_id, attempt)`.

Zero-cost private validation passed:

- static readiness: 24 tasks, 12 O / 12 W, eight families, r1/r2/r3 complete;
- gold: 24/24;
- generic fail: 0/24;
- outcome-slip fail: 0/24;
- protocol-slip fail: 0/24.

Official ranking moved back to confined `openrouter`.
`openrouter-shell` remains retired ablation evidence. The first paid step is
an eight-item, one-attempt, two-system canary, not a 24×3 sweep.

## Unresolved evidence

- The private bank is structurally and deterministically ready but has no live
  response matrix. Authored rung labels are hypotheses until weak, middle, and
  frontier systems identify item difficulty and discrimination.
- The retired v2 Fable records remain diagnostic only: the wave was manually
  aborted and that bank was one-track.
- Registry publication still requires three attempts, six live systems,
  same-channel item variance, band occupancy, and paired separation.
- Public hidden tests have no canary or encrypted/private counterpart.
- Deleted material inside macOS Trash could not be inspected because of system
  permissions; every other accessible Cursor store, backup, archive, and common
  export location was searched without finding another design session.

