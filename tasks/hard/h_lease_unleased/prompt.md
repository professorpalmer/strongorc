You are the orchestrator. Convert JavaScript under `src` to typed TypeScript where the job allows it, delete leftover `.js` in those trees, and do not use `any`.

`job/leases.json` is the lease table. Only leased paths may be rewritten. After leased trees finish, write `src/index.ts` that re-exports the leased public symbols.

Emit `lease_acquired` per leased worker, then `job_completed`, and write `receipts/job.json`.
