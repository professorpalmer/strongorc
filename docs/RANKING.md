# StrongOrc ranking contract

Harness **0.6.0**. Official ranking channel: confined OpenRouter
(`examples/openrouter_agent.py`). This file is the public contract for the
frozen ranking instrument. It is not a leaderboard.

## What is published

| Object | Public? |
| --- | --- |
| Harness, scorer, confined agent, practice slices | Yes |
| Scoring rules and publication gates | Yes |
| SHA-256 commitment of the private ranking bank | Yes |
| Private task files, prompts, oracles, gold agents, generators | No |
| Official model ranks on this bank | Not yet |

The private overlay stays outside git. Point `STRONGORC_HOLDOUT` at it.
`--slice ranking` refuses if the overlay is missing, incomplete, or does
not match the commitment below.

## Ranking bank commitment

- Card: [`cards/preregister/holdout-0.6.0-openrouter-ranking-v1.json`](../cards/preregister/holdout-0.6.0-openrouter-ranking-v1.json)
- Bank name: `strongorc-ranking-v1-2026-09-01`
- Schema: `ranking-v1`
- `private_bank_commitment_sha256`: `b4dee106cd5d442e23899c38adf122b54ad82f71163ff36770b7b71f9ee00110`

That hash is SHA-256 of the private `BANK_COMMITMENT.json` (sorted file
digests). Paid ranking checks every overlay file against that manifest.
A different bank is a different series.

Earlier `holdout-0.6.0-openrouter-frontier-v*.json` cards are superseded
calibration commitments. Do not score them as ranking.

## Instrument

24 opaque tasks (`hld_<hex>`): eight families × r1–r3, 12 orchestrator /
12 worker. Orchestrator tasks go through a parent-owned worker broker.
Worker tasks execute a frozen assignment. Live state is nonce-generated
before the model starts and may be revised after a harness interrupt.

Families are durable-orchestration fail classes, not coding puzzles:
`quorum_mask`, `clock_fence`, `wave_seal`, `child_closed` (O);
`witness_chain`, `epoch_bind`, `retract_cursor`, `trip_latch` (W).

## Scoring

A trial passes only if **outcome and protocol** both pass.

On the ranking slice, `task_equalized_score` is the mean of per-task
strict pass rates over non-censored attempts. Repeats of one task are
averaged first. That is the ranking number.

`task_evidence_score` keeps protocol-gated hidden-check evidence for
diagnosis. Interrupt survival and protocol vocabulary can zero an
outcome; they cannot add rank. Provider authentication, payment,
rate-limit, and refusal failures are coverage, not ability: they leave
the capability denominator and appear on `coverage_rate`,
`censored_attempts`, and `censor_reasons`.

Public practice cards still publish check-weighted `strongorc_score`.
That number is not the ranking headline. Cards from 0.5.x are not
comparable to 0.6.0.

Quote a number with slice, `harness_version`, adapter, confinement,
commitment hash, and uncertainty. Do not copy it into a product
`capability_score`.

## Uncertainty and gates

Primary intervals are paired, task-clustered bootstrap over per-task
pass rates. Do not rank two systems when the 95% interval on their
paired delta covers 0, or when the mean delta is below 0.10.

Publication gates on the ranking card:

- same confined OpenRouter channel only
- three attempts per task
- at least six live systems
- weak, middle, and frontier occupancy
- coverage ≥ 0.95
- fitted item screen with no rewrite/drop items required for a first
  public table
- `require_protocol_ready`

Target bands for interpretation, not for forcing a score:

| Band | Strict pass |
| --- | --- |
| Weak | 0.01–0.10 |
| Middle | 0.15–0.45 |
| Frontier | 0.50–0.75 |
| Saturated | ≥ 0.85 |

## Validation before any model

```bash
export STRONGORC_HOLDOUT=/path/to/private/overlay
python scripts/calibrate.py --slice ranking --validate-only \
  --preregister cards/preregister/holdout-0.6.0-openrouter-ranking-v1.json
```

`--slice ranking` without `--preregister` now selects that same card.
Scripted gold must be 24/24. Targeted fails (generic, outcome-slip,
protocol-slip, assignment-blind, protocol-only) must be 0/24.

## What is not a ranking score

- Public `brutal` / `native` / `ladder` / `reason` rows
- Retired `core` / `hard` / `frontier` rows
- Cursor SDK rows from a machine that can open this checkout
- OpenCode Go or `openrouter-shell` rows
- Development scores on the frontier-v6 calibration bank
  ([CALIBRATION_APPENDIX.md](CALIBRATION_APPENDIX.md))

Those last scores froze the design. They are not ranks on ranking-v1.
No live model has been scored on ranking-v1.
