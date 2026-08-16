You are the orchestrator. Start worker `left` on `src/left` and worker `right` on `src/right`.

Each worker writes `state/left.done` or `state/right.done`. Only then write `src/join.ts` exporting `join(n)` as `left(n) + right(n)` and emit `job_completed`.

Emit `worker_started`/`worker_finished` for both before the join.
