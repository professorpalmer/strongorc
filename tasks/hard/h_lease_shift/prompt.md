You are the orchestrator. Convert leased JavaScript under `src` to typed TypeScript, delete leftover `.js` in those trees, and do not use `any`.

`job/leases.json` is the lease table. Re-read it after every resume. After leased work finishes, write `src/index.ts` that re-exports `one` and `two`.

This job is interruptible. After the first leased tree is done, write `state/checkpoint.json` and wait.

Emit `lease_acquired` per leased worker, `checkpoint_written`, `resumed_from_checkpoint`, then `job_completed`, and write `receipts/job.json`.
