You are the orchestrator. Convert `src/left` and `src/right` to typed TypeScript and delete leftover `.js`.

`job/budget.json` is the worker budget for this job. Honor it.

Emit `worker_started` / `worker_finished` for the workers you actually start, then `job_completed`, and write `receipts/job.json`.
