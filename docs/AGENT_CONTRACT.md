# Agent contract (drop-day)

A live model run is a `command` adapter process. The harness seeds `DURABLE_ORCH_RUN_DIR` from `tasks/<slice>/<id>/seed/` and writes `PROMPT.md` there. You write artifacts into that directory, then exit 0.

## Required outputs

| Path | Rule |
| --- | --- |
| `protocol.jsonl` | One JSON object per line: `{"type": "<event>", "payload": {}}` |
| `receipts/job.json` | `status`, `model_id`, `usd`, `tokens_in`, `tokens_out`, `workers_ran` |

`model_id` must equal `DURABLE_ORCH_MODEL`. `status=completed` with `workers_ran=0` is a dead-swarm fail.

Selected tasks inject a per-run `nonce` into a seed JSON file (also copied to `.harness/nonce`). Required outputs must contain that nonce. Hardcoding the public seed is not enough.

## Environment

| Variable | Meaning |
| --- | --- |
| `DURABLE_ORCH_RUN_DIR` | Workspace root |
| `DURABLE_ORCH_TASK_ID` | e.g. `o_kill_resume` |
| `DURABLE_ORCH_TRACK` | `orchestrator` or `worker` |
| `DURABLE_ORCH_MODEL` | Invoked model id |
| `DURABLE_ORCH_PROMPT` | Path to the copied prompt |

## Event types

`checkpoint_written`, `resumed_from_checkpoint`, `job_completed`, `job_failed`, `job_refused`, `worker_started`, `worker_finished`, `orchestrator_wrote_solution`, `false_green`, `discovery_materialized`, `discovery_reused`, `llm_call`, `lease_acquired`, `lease_violated`, `wave_verified`, `wave_skipped`, `wave2_started`, `receipt_written`, `artifact_consumed`, `hollow_pass`

Forbidden types are task-specific. Emitting a forbidden type fails the trial even if the files look green.

## Scoring

`durable-orch grade` is offline. It does not call a model. Outcome files and protocol must both pass. See each task's `oracle.py` and `prompt.md`.
