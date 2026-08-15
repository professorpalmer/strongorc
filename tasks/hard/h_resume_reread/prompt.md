You are the orchestrator. Implement `src/scale.ts` from the job, delete leftover `.js`, and do not use `any`.

`job/spec.json` is the job. Re-read the workspace after every resume. Other state files may appear later.

This job is interruptible. After you have read the job, write `state/checkpoint.json` and wait before shipping the implementation.

Emit `checkpoint_written`, `resumed_from_checkpoint`, `artifact_consumed`, then `job_completed`, and write `receipts/job.json`.
