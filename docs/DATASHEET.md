# StrongOrc datasheet

Factsheet for the StrongOrc benchmark and its public task banks. Validity
belongs to the interpretation made from a score, not to the file layout.
Read with [SPEC.md](../SPEC.md). Status of published cards is taken only
from [cards/registry.json](../cards/registry.json).

This follows the spirit of Gebru et al., “Datasheets for Datasets”
(2021), Mitchell et al., “Model Cards for Model Reporting” (2019), and
Reuel et al., “BetterBench” (2024). It is a benchmark factsheet, not a
generic dataset card and not a model card.

## 1. Construct and subcomponents

StrongOrc measures *durable orchestration*:

1. **O (orchestrator)** — decompose, lease, checkpoint, resume, verify,
   and receipt without writing the worker’s solution.
2. **W (worker / leaf)** — consume materialized artifacts, write
   structured ones, respect a lease, resume from objects, and refuse
   honestly.

A trial passes only if **outcome and protocol** both pass. Practice cards
retain `strongorc_score`, the legacy check-weighted diagnostic. The private
ranking headline is `task_equalized_score`: the mean of per-task strict pass
rates over non-censored attempts. `task_evidence_score` keeps protocol-gated
hidden outcome evidence as a diagnostic. Interrupt and protocol-shape rates
do not add ranking credit. Provider infrastructure failures are coverage.
See [RANKING.md](RANKING.md).

Subcomponents (fail classes, not product features): false-green and $0
dead-swarm; planner-plays; skipped wave-boundary; lease collision or
escape; dishonest receipt; hollow pass; ignored discovery; replay from
scratch; missed live kill / resume; post-kill rewrite blindness.

Sibling research: *State, Not Tokens* (Zenodo 10.5281/zenodo.20709565).
Independent package — not a Puppetmaster module.

## 2. Task provenance

Tasks were authored for this harness. Method was borrowed; instances
were not.

| Source | Taken | Not taken |
| --- | --- | --- |
| SWE-bench | Hidden-test spirit, frozen predictions, keyless regrade | Issue/PR instances |
| DeepSWE | Difficulty that should not saturate | Coding-agent leaderboard identity |
| Terminal-Bench | Long horizon, killable environment | Terminal puzzles |
| NL2Repo | Repo-scale oracle, hidden upstream tests | Their library instances |
| State, Not Tokens | One independent variable, unforgeable oracle, no LLM-as-judge | JS→TS as the definition of this bench |

Public slices live under `tasks/<slice>/`. Each task directory holds
`task.json`, `prompt.md`, `seed/`, `oracle.py`, and (when used)
`hidden/`, `agents/{pass,fail}.py`. Scripted personas prove oracles are
not vacuous; they are not model results.

The private holdout is minted outside this checkout. It contains opaque task
ids, nonce-bound generators, gold and targeted-failure personas, private
oracles, and harness-owned worker pools. Only `tasks/holdout/README.md` is
public. Official ranking is committed by
`b4dee106cd5d442e23899c38adf122b54ad82f71163ff36770b7b71f9ee00110` in
[`holdout-0.6.0-openrouter-ranking-v1.json`](../cards/preregister/holdout-0.6.0-openrouter-ranking-v1.json).
Paid runs refuse a different bank.

Authoring chronology and saturation evidence: [STRONGORC_HISTORY.md](STRONGORC_HISTORY.md).
Measurement notes: [BENCHMARK_METHODS.md](BENCHMARK_METHODS.md).

## 3. Intended uses

- Same-harness comparison of systems as orchestrators and as leaves, on
  **one named slice** and **one `harness_version`**.
- Oracle non-vacuity (scripted `pass` / `fail`) and keyless regrade of
  frozen `cards/raw/*.jsonl`.
- Same-harness calibration (`strongorc calibrate`): response matrix,
  task-pass curves, check-grain curves, and IRT only after live systems
  exist on one channel. Cursor SDK rows from this checkout are a
  leak-diagnostic series. OpenCode Go (`agentic-opencode`) is a
  separate adapter-dialect series (isolated cwd, no `emit_event`).
  OpenRouter (`examples/openrouter_agent.py`) is the confined tool
  jail. Do not mix them.
- Dated overlays after a same-test run: `orch_score` / `leaf_score`,
  harness SHA, date, adapter, confinement, contamination.
- Calibration and ranking on the private rotating holdout. Do not author or
  copy that bank into this checkout.

Quote a number with slice, `harness_version`, adapter, confinement, and
uncertainty. In-house registry cards, if any, come from a confined
agent that cannot read this checkout. Practice slices are `brutal`,
`native`, `ladder`, and `reason`. The ranking slice is `holdout`.
`core` / `hard` / `frontier` are retired evidence. Default CLI slice
is `ladder`. Default live channel is OpenRouter.

## 4. Explicit non-claims

A StrongOrc number does **not** mean:

- general intelligence, “agent skill,” or a foundation-model ranking
- software-engineering skill (not SWE-bench / DeepSWE)
- product `capability_score` or a vendor workhorse claim
- anti-cheat, contamination-proof, or “the model never saw the tests”
- that a high `leaf_score` is orchestrator competence, or the reverse
- that checks inside one task are independent Bernoulli trials
- that cards from harness 0.5.x (or earlier) compare to 0.6.0
- that slices compare to each other

`exists:` plus `job_completed` is participation, not rank. Hidden tests
in this git tree are plaintext. Relocating `--runs-dir` does not hide
the checkout from an authoring-machine SDK.

## 5. Composition by slice

| Slice | Role | Size | Oracle grain | Registry |
| --- | --- | --- | --- | --- |
| `core` | Oracle ritual | 12 (6 O / 6 W) | Protocol toys | Non-model baselines only |
| `hard` | Destuped floor | 16 (9 O / 7 W) | Node + hidden | Retired evidence |
| `frontier` | Destuped-plus JS/TS | 48 | Node + hidden | Retired evidence (outcome saturated) |
| `brutal` | Library-hidden checkpoint | 8 (4 O / 4 W) | Hidden pytest, 47 cases | Public practice |
| `native` | Orchestration-protocol series | 12 (6 O / 6 W) | Hidden pytest, 96 cases | Public practice |
| `ladder` | Native families × r1–r4 | 48 (24 O / 24 W) | Hidden pytest, 384 cases | Public practice; 36-task cards are not comparable |
| `reason` | Evidence-quality rungs | 12 (4 families × r1–r3) | Hidden pytest, 96 opaque ids | Public practice (plaintext; may leak) |
| `holdout` | Private frontier bank | 24 (12 O / 12 W; 8 families × r1–r3) | Nonce-generated hidden outcomes plus sealed broker/interrupt evidence | Ranking set; never in git |

`reason` rungs change evidence quality, not file/lane/decoy width: r1
induces a contract from partial traces; r2 revises after a sealed
post-kill contradiction; r3 must write a discriminating
`state/probe.json`. Scripted `pass` interprets live objects. There is
no `hidden/reference` gold.

## 6. Adapters and confinement

The bench is adapter-agnostic. Puppetmaster may be *a* command adapter.
It is not the definition of a pass.

| Adapter | Role |
| --- | --- |
| `scripted` | Deterministic `pass` / `fail` personas |
| `command` | External agent with `STRONGORC_RUN_DIR` (drop-day hook) |

Confinement is a measurement field (`unknown`, `confined`,
`unconfined`, `authoring_sdk`, `scripted`). `command` + `authoring_sdk`
cannot claim `contamination=clean` or `registry_status=clean`.
`unconfined` is the OpenRouter agent plus `run_command` in the run dir
(`openrouter-shell`). It is a jail-ablation series, not a leak and not
mixable with confined jsonl. Live registry cards need an agent that
cannot open `tasks/*/hidden`. Agent contract:
[AGENT_CONTRACT.md](AGENT_CONTRACT.md).

## 7. Contamination

Public hidden tests, references, and oracles are in this repository.
Treat live cards as same-test evidence, not an anti-cheat contest.

- **authoring_leak** — agent could read this tree (Cursor SDK on the
  authoring machine). Cards stay as leak diagnostics.
- **unknown** — default. Never inferred as clean from a score.
- **clean** — only by an explicit registry claim after a confined
  channel. The inventory currently contains none.

A per-run `nonce` binds selected outputs. Most protocol events are
still agent-authored. On interrupt tasks the harness SIGKILLs, writes
`.harness/killed` and `.harness/pre_kill_{i}.json`, and grade requires
those sealed files. Grade also requires parent-observed kill counts and
pre-kill snapshot digests on the frozen trial; agent-writable files are
not enough. Private orchestrator tasks additionally require worker dispatch
and report consumption recorded by the parent-owned broker; self-authored
`worker_started`, `artifact_consumed`, or `workers_ran` cannot satisfy those
checks. Worker tasks instead receive an immutable orchestrator assignment.

## 8. Scoring and uncertainty

`strongorc grade` is the only scorer. Frozen `TrialRecord.files` regrade
without API keys or `runs/`. Cards take `harness_version` from the
trials, not from the grading install.

Primary uncertainty is **task-clustered bootstrap** (1000 resamples,
seed 0): resample unique `task_id`s, keep every attempt of each draw.
Unanimous all-pass / all-fail samples cannot estimate variance by
resampling tasks alone; those primary intervals are widened with a
task-level Wilson envelope so a finite all-pass card is not `[1, 1]`
and a finite all-fail card is not `[0, 0]`. Wilson 95% intervals on
check-level pillars treat checks as independent and are too narrow when
many checks share a package. On ranking, `task_equalized_score` is the strict-pass headline.
`--repeats N` fills `pass_at_1` / `pass_at_k`. Do not rank two systems
when paired task-level uncertainty does not separate them. Development
scores on the earlier frontier-v6 bank are in
[CALIBRATION_APPENDIX.md](CALIBRATION_APPENDIX.md) and are not ranks.

Cards from 0.5.x are not comparable to 0.6.0. The 0.6.0 headline
changed what counts as evidence and how honesty gates the number.

## 9. Maintenance and retirement

| Status in `cards/registry.json` | Meaning |
| --- | --- |
| `unknown` | Published; not reviewed as clean |
| `leak_diagnostic` | Channel could see the tree |
| `retired_evidence` | Saturated, superseded, or wrong grain; keep as history |
| `non_model` | Scripted oracle baseline, not a model result |
| `clean` | Explicit confined claim only; never inferred |

Retirement is recorded on the registry entry (`retirement_reason`),
not inferred from the filename. `hard` and `frontier` are evidence-only.
Scripted cards are `non_model`. Composer brutal cards from the
authoring machine are `leak_diagnostic`.

Frozen raw trials belong in `cards/raw/*.jsonl` (gitignored globally as
`*.jsonl`, with an exception for that directory only). Do not unignore
`.env`, holdout banks, or secrets.

This package is MIT, versioned in `pyproject.toml` (`0.6.0` on this
tree). A `CITATION.cff` is withheld until a tagged `main` release and
its author/version metadata are verified.

## 10. Private holdout

`STRONGORC_HOLDOUT` points at an overlay **outside git**. Public
`tasks/holdout` is the operator README only. Real banks, generators,
references, and `oracle.py` stay out of the repository. Unset or
uncommitted overlay refuses `run` / `card` rather than scoring 0/0.
`tests/fixtures/holdout_overlay` is a non-secret miniature used in CI.
CI must not require a real holdout.

## 11. Review and contact

Public oracles have not received a documented independent dual review.
Disagreements and underspecification are not yet a standing log.
Scripted `fail` names a check per task; that is the current
deterministic audit.

Issues and cards: https://github.com/professorpalmer/strongorc

Author (package metadata): Cary Palmer. License: MIT (2026).
Do not treat this datasheet as a peer-reviewed instrument report.
