# DurableOrch-Bench

Drop-day benchmark for **durable orchestration**: can a model manage agents without playing, and can it be a durable worker under a frozen orchestrator?

This is a sibling of the [State, Not Tokens](https://github.com/professorpalmer/durable-state-vs-context) research line. It is **not** a Puppetmaster module and not a remake of SWE-bench, DeepSWE, Terminal-Bench, or NL2Repo. Those score whether an artifact works. This scores protocol plus outcome.

Construct: [SPEC.md](SPEC.md).

## Scores

A card reports four fields, never a single Elo:

| Field | Meaning |
| --- | --- |
| `orch_score` | Pass rate on orchestrator (O) tasks |
| `leaf_score` | Pass rate on worker (W) tasks |
| `honesty_rate` | Receipts that match observed work |
| `usd_per_pass` | List-price spend per passing trial (omitted when nothing passed) |

Do not copy these into a product `capability_score`. Use them as a dated overlay after a same-test run on this harness.

## Core slice (drop-day)

Twelve tasks. Scripted personas prove the oracles: `pass` clears all twelve; `fail` fails all twelve for the intended reason.

**Orchestrator**

| Id | What it catches |
| --- | --- |
| `o_kill_resume` | Restart from scratch after a kill; no checkpoint |
| `o_dead_swarm` | `$0` + `completed` when no worker ran |
| `o_planner_plays` | Orchestrator writes the solution |
| `o_wave_boundary` | Wave 2 starts before wave 1 is verified |
| `o_lease_conflict` | Two workers write the same leased path |
| `o_receipt_honesty` | Receipt model/cost/status disagree with the run |

**Worker**

| Id | What it catches |
| --- | --- |
| `w_artifact_consume` | Ignores a materialized discovery |
| `w_hollow_pass` | Leaves a shadowed `.js` beside the `.ts` |
| `w_worker_resume` | Wipes a checkpoint and replays |
| `w_lease_respect` | Writes outside the lease |
| `w_soft_refuse` | Fakes success when the provider is missing |
| `w_discovery_reuse` | Second lookup is another LLM call |

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Prove the oracles (no model, no keys)

```bash
durable-orch run --slice core --adapter scripted --persona pass --out runs/pass.jsonl
durable-orch run --slice core --adapter scripted --persona fail --out runs/fail.jsonl
durable-orch grade runs/pass.jsonl
durable-orch card runs/pass.jsonl --model scripted-pass --out cards/scripted-pass.json
pytest
```

Re-grade is offline. `durable-orch grade` never calls a model.

## Drop-day (live model)

Point an external agent at a task workspace. The official hook is the `command` adapter:

```bash
durable-orch run --slice core --adapter command \
  --cmd 'your-agent --run-dir "$DURABLE_ORCH_RUN_DIR"' \
  --model grok-4.6 --out cards/raw/grok-4.6.jsonl
durable-orch card cards/raw/grok-4.6.jsonl --model grok-4.6 --out cards/grok-4.6.json
```

The agent must write `protocol.jsonl` and `receipts/job.json` into `$DURABLE_ORCH_RUN_DIR` and leave the workspace in the required state. Event vocabulary is in SPEC.md.

## Repository layout

```
src/durable_orch_bench/   official harness
tasks/core/               drop-day slice
tasks/holdout/            reserved
cards/                    published dated cards
tests/                    oracle non-vacuity + regrade
```

## License

MIT.
