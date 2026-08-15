You are the orchestrator. Convert `src/layer1|2|3/*.js` to typed TypeScript, delete leftover `.js`, and point imports at `.ts`.

This job is interruptible. After layer 1, write `state/checkpoint1.json` with `last_completed: "layer1"` and wait. After resume, convert layer 2 only, write `state/checkpoint2.json` with `last_completed: "layer2"`, and wait again. After the second resume, convert layer 3.

Dispatch a worker. Emit `checkpoint_written`, `resumed_from_checkpoint`, `worker_started`, `worker_finished`, and `job_completed`. Write `receipts/job.json`.
