# Agent contract (drop-day)

A live model run is a `command` adapter process. The harness seeds `STRONGORC_RUN_DIR` from `tasks/<slice>/<id>/seed/` and writes `PROMPT.md` there. You write artifacts into that directory, then exit 0.

## Required outputs

| Path | Rule |
| --- | --- |
| `protocol.jsonl` | One JSON object per line: `{"type": "<event>", "payload": {}}` |
| `receipts/job.json` | `status`, `model_id`, `usd`, `tokens_in`, `tokens_out`, `workers_ran` |

`model_id` must equal `STRONGORC_MODEL`. `status=completed` with `workers_ran=0` is a dead-swarm fail.

Selected tasks inject a per-run `nonce` into a seed JSON file (also copied to `.harness/nonce`). Required outputs must contain that nonce. Hardcoding the public seed is not enough.

## Environment

Live `command` runs must not see the bench checkout. If `--runs-dir` is inside the repo, the harness relocates it to `~/.strongorc/runs/<name>`. Hidden tests and references are not in the seed.

The harness writes both `STRONGORC_*` and legacy `DURABLE_ORCH_*` names. Read either.

| Variable | Meaning |
| --- | --- |
| `STRONGORC_RUN_DIR` | Workspace root |
| `STRONGORC_TASK_ID` | e.g. `o_kill_resume` |
| `STRONGORC_TRACK` | `orchestrator` or `worker` |
| `STRONGORC_MODEL` | Invoked model id |
| `STRONGORC_PROMPT` | Path to the copied prompt |
| `STRONGORC_RESUME` | `1` after the harness SIGKILLs an interrupt task; unset/`0` on the first spawn |
| `STRONGORC_RESUME_STEP` | Kill index just survived (`1`, `2`, …) on a resume spawn |
| `STRONGORC_EXPECT_INTERRUPT` | `1` when this spawn has a harness kill; `0` on rungs with no interrupt. Do not `wait` when it is `0`. |

`STRONGORC_HOLDOUT` is an **operator** variable. It names an external overlay
root for the private holdout slice. The harness strips it from the agent
process environment. Agents never receive overlay paths, hidden tests,
generators, or references. Do not commit a real holdout bank to this
repository. Public `tasks/holdout` is the operator README only. When
the variable is unset, holdout
is empty and `run` / `card` refuse a vacuous score. Overlay generators
are trusted grader-side code loaded in-process — not a sandbox. Grade
hashes the overlay before and after `generate` and jails the returned
path; overlay mutation or an escaped path fails closed.

## Event types

`checkpoint_written`, `resumed_from_checkpoint`, `harness_killed`, `job_completed`, `job_failed`, `job_refused`, `worker_started`, `worker_finished`, `orchestrator_wrote_solution`, `false_green`, `discovery_materialized`, `discovery_reused`, `llm_call`, `lease_acquired`, `lease_violated`, `wave_verified`, `wave_skipped`, `wave2_started`, `wave2_verified`, `wave3_started`, `receipt_written`, `artifact_consumed`, `hollow_pass`

On interrupt tasks the harness SIGKILLs after each `when_file` appears (one step, or a chain), writes `.harness/killed` plus `pre_kill_<n>.json`, records parent-observed kill counts and snapshot digests on the trial, emits `harness_killed`, then respawns with `STRONGORC_RESUME=1`. Grade requires that parent evidence plus matching sealed files (`sealed:harness_killed`, `sealed:pre_kill_<n>`, `sealed:kill_count`). Writing `harness_killed` into `protocol.jsonl` or forging `.harness` files without parent evidence does not pass. An interrupt step may `rewrite`, `plant`, or `delete` files after the kill. Re-read the workspace. Do not replay the first prompt from memory. Do not finish the whole job before the last checkpoint.

The oracle re-runs hidden pytest on practice slices (brutal, native, ladder, reason). hard and frontier also re-run Node tests; those slices are retired evidence. The ranking set is the private holdout. Hidden tests are not in the seed. A visible `print("ok")` / `console.log("ok")` is not a pass. On brutal / native / ladder / reason, the work is a real Python package. Re-read `job/leases.json` and `job/budget.json` after every interrupt. If `job/cancel.json` appears or `unsafe` is true, refuse.

Forbidden types are task-specific. Emitting a forbidden type fails the trial even if the files look green.

## Scoring

`strongorc grade` is offline. It does not call a model. Outcome files and protocol must both pass. See each task's `oracle.py` and `prompt.md`. Holdout grade-time cases are regenerated from the overlay generator and the frozen harness nonce; they never rewrite `TrialRecord.files`. Regrading holdout still requires `STRONGORC_HOLDOUT`.
