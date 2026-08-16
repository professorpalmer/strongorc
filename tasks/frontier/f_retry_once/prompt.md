You are the orchestrator. Convert `src/retry/job.js`.

You may emit `worker_started` at most twice (one retry). A third start fails the budget.

Emit `job_completed`.
