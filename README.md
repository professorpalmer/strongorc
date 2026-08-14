<p align="center"><img src="brand/strongorc.svg" width="200" alt="StrongOrc"></p>
<h1 align="center">StrongOrc</h1>
<p align="center">Can a model manage agents without playing, and can it be a durable worker under a frozen orchestrator?</p>

This is a sibling of the [State, Not Tokens](https://github.com/professorpalmer/durable-state-vs-context) research line. It is **not** a Puppetmaster module and not a remake of SWE-bench, DeepSWE, Terminal-Bench, or NL2Repo. Those benches lent *method* (hidden tests, frozen predictions, containers, repo-scale oracles). The tasks are ours: kill-resume, dead-swarm, planner-plays, wave-boundary, leases, receipts, artifact consume, hollow pass, worker resume, lease respect, soft-refuse, discovery reuse. **core** is the oracle ritual. **hard** is the drop-day / registry run — real SIGKILL, leftover-`.js` hollow fails, and Node tests the oracle re-runs.

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

## Core slice (oracle ritual)

Twelve tasks. Scripted personas prove the oracles: `pass` clears all twelve; `fail` fails all twelve for the intended reason. A live model can still emit the event vocabulary without doing the work. Do not publish routing cards from `core` alone.

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

## Hard slice (drop-day / own-use registry)

Four tasks with real trees. The harness SIGKILLs `h_kill_resume` after layer 1 is checkpointed, then respawns with `STRONGORC_RESUME=1`. Oracles re-run Node (`--experimental-strip-types`). Finishing the whole job in one shot, leaving a shadowed `.js`, or starting wave 2 before a real wave-1 test passes are fails.

| Id | Track | What it catches |
| --- | --- | --- |
| `h_kill_resume` | O | Converts all 12 files before the kill; no resume; layer-1 hashes drift |
| `h_hollow_migration` | W | Writes `.ts` but leaves the `.js` |
| `h_wave_gate` | O | Implements `mul` before `test/wave1.mts` exits 0 |
| `h_lease_tree` | O | Two workers collide on `src/shared/CONFLICT` |

```bash
strongorc run --slice hard --adapter scripted --persona pass --out runs/hard-pass.jsonl
strongorc run --slice hard --adapter command \
  --cmd 'your-agent --run-dir "$STRONGORC_RUN_DIR"' \
  --model grok-4.6 --out cards/raw/grok-4.6-hard.jsonl
strongorc card cards/raw/grok-4.6-hard.jsonl --model grok-4.6 --slice hard --out cards/grok-4.6-hard.json
```

Needs Node 22+ on the grading machine.

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Prove the oracles (no model, no keys)

```bash
strongorc run --slice core --adapter scripted --persona pass --out runs/pass.jsonl
strongorc run --slice hard --adapter scripted --persona pass --out runs/hard-pass.jsonl
strongorc run --slice core --adapter scripted --persona fail --out runs/fail.jsonl
strongorc grade runs/pass.jsonl
strongorc card runs/hard-pass.jsonl --model scripted-pass --slice hard --out cards/scripted-hard-pass.json
pytest
```

Re-grade is offline. `strongorc grade` never calls a model.

## Drop-day (live model)

Point an external agent at a task workspace. The official hook is the `command` adapter:

```bash
strongorc run --slice hard --adapter command \
  --cmd 'your-agent --run-dir "$STRONGORC_RUN_DIR"' \
  --model grok-4.6 --out cards/raw/grok-4.6.jsonl
strongorc card cards/raw/grok-4.6.jsonl --model grok-4.6 --slice hard --out cards/grok-4.6.json
```

The agent must write `protocol.jsonl` and `receipts/job.json` into `$STRONGORC_RUN_DIR` and leave the workspace in the required state. Event vocabulary and the nonce-bind rule are in [SPEC.md](SPEC.md) and [docs/AGENT_CONTRACT.md](docs/AGENT_CONTRACT.md). `DURABLE_ORCH_*` env names still work as aliases.

## Repository layout

```
brand/                    StrongOrc mark (SVG + PNG)
src/strongorc/            official harness
tasks/core/               oracle ritual (twelve toys)
tasks/hard/               drop-day / registry run
tasks/holdout/            reserved
cards/                    published dated cards
tests/                    oracle non-vacuity + regrade
```

## License

MIT.
