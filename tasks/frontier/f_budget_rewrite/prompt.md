You are the orchestrator. Convert `src/left` and `src/right`.

`job/budget.json` caps `worker_started` events. Checkpoint after the first worker. Re-read the budget after any interrupt. Do not start more workers than the live cap.

You may finish the remaining tree without a second `worker_started` if the cap is 1.

Emit `job_completed`.
