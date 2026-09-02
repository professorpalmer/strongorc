<p align="center">
  <img src="brand/strongorc-react-flex.gif" width="240" alt="StrongOrc flexing">
</p>
<h1 align="center">StrongOrc</h1>
<p align="center">Can a model manage agents without playing?<br>Can it be a durable worker under a frozen orchestrator?</p>

A drop-day bench for **durable orchestration**. Outcome is necessary. Protocol honesty is first-class. A trial passes only if both do.

This is a sibling of [State, Not Tokens](https://github.com/professorpalmer/durable-state-vs-context). It is not a Puppetmaster module and not a remake of SWE-bench, DeepSWE, Terminal-Bench, or NL2Repo. Those benches lent method. The tasks are ours.

Construct: [SPEC.md](SPEC.md). Ranking contract: [docs/RANKING.md](docs/RANKING.md). Datasheet: [docs/DATASHEET.md](docs/DATASHEET.md). Agent hook: [docs/AGENT_CONTRACT.md](docs/AGENT_CONTRACT.md). Registry: [cards/registry.json](cards/registry.json) is authoritative for retired, non-model, and leak-diagnostic status — never infer `clean` from a filename or a score.

## Card

Public practice cards retain `strongorc_score` (harness 0.6.0): the check-weighted evidence rate over hidden, interrupt, and protocol-shape checks, multiplied by `honesty_rate_earned`. Private ranking uses `task_equalized_score` as the mean of per-task **strict pass** rates (outcome and protocol) over non-censored attempts. Protocol-gated hidden evidence stays diagnostic. Interrupt and protocol vocabulary cannot add rank credit. Cards from 0.5.x are not comparable to 0.6.0. There is no official ranking table yet.

| Field | Meaning |
| --- | --- |
| `strongorc_score` | Evidence rate (hidden + interrupt + shape) x earned-honesty gate (the StrongOrc number) |
| fingerprint | `trials% hidden% interrupt% protocol_shape% honesty_earned%` |
| `hidden_rate` | Hidden tests one-by-one (brutal: 47 cases; native: 96; ladder: 384) |
| `interrupt_rate` | Kill / resume / checkpoint order |
| `protocol_shape_rate` | Hard-grain checks that are neither hidden nor interrupt |
| `honesty_rate_earned` | Honesty checks on trials where the agent claimed work |
| `honesty_rate` | All-trial honesty, including harness-authored failures (not headline) |
| `orch_score` / `leaf_score` | Trial pass rates (O / W) |
| `hard_rate` | Hidden + interrupt + protocol-shape |
| `layout_rate` | `exists:` only — not a headline |
| `outcome_rate` / `protocol_rate` | Trial-level outcome / protocol |
| `outcome_check_rate` / `protocol_check_rate` | Hard-grain checks of that kind |
| `orch_check_rate` / `leaf_check_rate` / `task_check_rates` | Hard-check pass rates |
| `usd_per_pass` | List-price spend per passing trial |
| `facet_scores` | Per-fail-class trial pass rates |
| `facet_check_scores` | Per-fail-class hard-check pass rates |
| `pass_at_1` / `pass_at_k` / `n_attempts` | Repeat-run pass rates (`--repeats N`) |
| `task_equalized_score` | Per-task mean of gated headline evidence (repeats averaged first; `strongorc_score` stays check-weighted) |
| `family_scores` / `rung_scores` | Trial pass rates parsed from ids such as `l_wave_seal_r4` (empty when no `_rN` suffix) |
| `tasks_passed` / `tasks_total` | Unique-task pass@1 counts (first attempt), not attempt totals |
| `<pillar>_ci` / `strongorc_score_ci` | Wilson 95% on pillars; bootstrap 95% on the headline |

Do not copy these into a product `capability_score`. Use them as a dated overlay after a same-test run on this harness.

Practice slices are **brutal**, **native**, **ladder**, and **reason**. They live in this tree with plaintext hidden tests; they may leak and they may saturate. Public `reason` is the current balanced O/W development instrument. The ranking set is a private **holdout** (`--slice ranking`), never authored here. Live ranking refuses until the overlay matches the SHA-256 commitment in [`cards/preregister/holdout-0.6.0-openrouter-ranking-v1.json`](cards/preregister/holdout-0.6.0-openrouter-ranking-v1.json). `--slice practice` sweeps the public four for development; it is not a score. The default CLI slice is `ladder`. **core**, **hard**, and **frontier** are retired evidence. Quote a StrongOrc number with slice, `harness_version`, adapter, confinement, and (for ranking) the bank commitment. Development scores on an earlier private bank are labeled in [docs/CALIBRATION_APPENDIX.md](docs/CALIBRATION_APPENDIX.md) and are not ranks.

## Live channel

The only clean live path in this tree is the confined tool jail: tools locked to `$STRONGORC_RUN_DIR`, no shell, no parent-repo reads, grade verbs in the tool list. Cursor SDK on a machine that can open this clone can read `tasks/*/hidden` — those cards stay leak diagnostics. OpenCode Go is isolated cwd plus shell, without `emit_event`; it scores a different dialect. Do not mix the three into one series. `scripts/calibrate.py` defaults to `--channel openrouter`. `--slice practice` runs the four public slices separately (not a ranking). `--slice ranking` is holdout and refuses without `STRONGORC_HOLDOUT`.

## Brutal slice

Eight tasks. NL2Repo method, our orch traps. Each task is a real Python package scored by a hidden pytest suite the seed never contains. README, discoveries, and post-kill rewrites look official and are wrong. Package names do not name the algorithm. Visible tests are hollow. Timeouts are 30 minutes. Scripted `pass` clears the slice; scripted `fail` misses `pytest:hidden`. This stays the library-hidden registry instrument. Native is the orchestration-protocol series.

```bash
strongorc run --slice brutal --adapter scripted --persona pass --out runs/brutal-pass.jsonl
strongorc card runs/brutal-pass.jsonl --model scripted-pass --slice brutal
```

## Native slice

Twelve tasks (six O, six W). Same hidden-pytest contract as brutal, but the payload is an orchestration protocol: wave seal, join hold, path mutex, dead child, live token, cap shift, ordered slips, idempotent pad, trip latch, resume cursor, sealed lease, planted query. Package names do not name the algorithm. Seeds lie. W-track oracles omit kill events; grade still requires sealed `.harness` kill files on interrupt tasks. Scripted `pass` clears the slice; scripted `fail` misses `pytest:hidden`. Quote StrongOrc with slice and `harness_version`. Native cards are a separate series from brutal.

```bash
strongorc run --slice native --adapter scripted --persona pass --out runs/native-pass.jsonl
strongorc card runs/native-pass.jsonl --model scripted-pass --slice native
```

## Ladder slice

Forty-eight tasks (four rungs × twelve native fail-class families). r1–r3 scale mechanical difficulty only — lane depth, join sides, stall width, planted children, fence rotations, live cap, slip sequence, decoys, trip constants, ack prefix, sealed-set size, compiled query contract. r4 inverts the live contract after a kill (descending seals, product gather, closed yard, refuse-on-all-ok, generation-bound token, cap 0, descending slips, replay raises, trip-on-two, reverse pending, helper-only extract, glob/OR query). Hidden pytest is the contract (384 cases). Scripted `pass` clears every rung; scripted `fail` misses `pytest:hidden`. W-track oracles omit kill events; grade still requires sealed `.harness` kill files on interrupt tasks. Multi-kill rungs emit `interrupt` as a list. Quote StrongOrc with slice and `harness_version`. Cards from the 36-task ladder are not comparable.

```bash
strongorc run --slice ladder --adapter scripted --persona pass --out runs/ladder-pass.jsonl
strongorc card runs/ladder-pass.jsonl --model scripted-pass --slice ladder
```

## Reason slice

Twelve tasks (four families × r1–r3; six O, six W). Public practice slice: evidence-quality rungs, not file/lane/decoy width. Not a registry ranking. r1 induces a contract from partial traces, r2 revises after a sealed post-kill contradiction, r3 must write a discriminating `state/probe.json` before committing. Hidden pytest uses 96 opaque `test_case_*` ids. Scripted `pass` interprets live objects; there is no `hidden/reference` gold.

```bash
strongorc run --slice reason --adapter scripted --persona pass --out runs/reason-pass.jsonl
strongorc card runs/reason-pass.jsonl --model scripted-pass --slice reason
python scripts/calibrate.py --slice reason --scripted
python scripts/calibrate.py --slice reason --validate-only
python scripts/calibrate.py --slice reason --channel openrouter --live stealth/ox-alpha --max-usd-per-task 1
```

Scripted pass/fail is oracle non-vacuity. Item difficulty is not
calibrated until a confined weak/mid/frontier matrix exists. Cursor SDK
rows from this checkout are leak diagnostics and are a different series.

## Core slice

Twelve toys that prove the oracles. Scripted `pass` clears all twelve; `fail` misses a named check. A live model can still emit the event vocabulary without doing the work.

| Orchestrator | Worker |
| --- | --- |
| `o_kill_resume` — no checkpoint | `w_artifact_consume` — ignores a discovery |
| `o_dead_swarm` — `$0` + `completed` | `w_hollow_pass` — leftover `.js` |
| `o_planner_plays` — writes the solution | `w_worker_resume` — replays from scratch |
| `o_wave_boundary` — skips verify | `w_lease_respect` — writes outside the lease |
| `o_lease_conflict` — two writers, one path | `w_soft_refuse` — fakes success |
| `o_receipt_honesty` — receipt lies | `w_discovery_reuse` — second lookup is an LLM call |

## Retired slices

`core` is the oracle ritual. `hard` (16 destuped JS tasks) and `frontier` (48 destuped-plus) stay in the tree as evidence. A confined jail row can look strong on them. Do not quote those scores as StrongOrc rank.

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

```bash
strongorc run --slice ladder --adapter scripted --persona pass --out runs/ladder-pass.jsonl
strongorc card runs/ladder-pass.jsonl --model scripted-pass --slice ladder
pytest
python scripts/replicate.py
```

`strongorc grade` never calls a model. `durable-orch` still works as a CLI alias.

## Live model

Practice (public, confined jail):

```bash
python scripts/calibrate.py --slice practice --live stealth/ox-alpha --max-usd-per-task 1
```

Ranking uses a private overlay and the confined OpenRouter channel. Authoring
code, ids, metadata, gold agents, worker pools, and oracles stay outside this
repository. The public commitment is
`b4dee106cd5d442e23899c38adf122b54ad82f71163ff36770b7b71f9ee00110`.
Validate before any model process can start:

```bash
export STRONGORC_HOLDOUT=/path/to/private/overlay
python scripts/calibrate.py --slice ranking --validate-only
python scripts/calibrate.py --slice ranking --live MODEL --initial-cell \
  --repeats 1 --jobs 2 --max-usd-per-task 1
```

`--slice ranking` defaults to confined `openrouter` and the ranking-v1
preregister card. `openrouter-shell` is a retired jail ablation, not an
official score. Live jsonl persists each `(task_id, attempt)` so a killed
wave resumes without dropping repeats or repaying completed attempts.
Paid ranking verifies every private-bank file against that commitment.

```bash
strongorc run --slice ladder --adapter command \
  --cmd 'python examples/openrouter_agent.py' \
  --model stealth/ox-alpha \
  --runs-dir ~/.strongorc/runs/ladder-live \
  --out cards/raw/ox-alpha-ladder.jsonl \
  --confinement confined
strongorc card cards/raw/ox-alpha-ladder.jsonl \
  --model stealth/ox-alpha --slice ladder \
  --confinement confined \
  --out cards/ox-alpha-ladder.json
```

A `--runs-dir` inside this checkout is relocated for the command adapter. Scripted personas may keep using `runs/`.

Write `protocol.jsonl` and `receipts/job.json` into `$STRONGORC_RUN_DIR`. `DURABLE_ORCH_*` env names are aliases.

## License

MIT.
