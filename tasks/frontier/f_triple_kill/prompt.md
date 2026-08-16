You are the orchestrator. Convert each `src/layerN` tree to typed TypeScript, one layer at a time.

Write `state/checkpointN.json` after layer N. Do not start the next layer until that checkpoint exists. Do not finish the job in one shot.

Emit `checkpoint_written` after each layer you complete, `resumed_from_checkpoint` when you continue, then `job_completed` and `receipts/job.json`.
