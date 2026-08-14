You are the orchestrator. Convert `src/alpha/*.js` and `src/beta/*.js` to typed TypeScript and delete the `.js` sources. `job/leases.json` assigns `src/alpha` to worker alpha and `src/beta` to worker beta. Do not let either worker write the other's tree.

After both leases finish, write `src/index.ts` that re-exports `one`, `inc`, `two`, and `dec`. Do not write `src/shared/CONFLICT`.

The oracle re-runs `test/test.mts`. Emit `lease_acquired` per worker, then `job_completed`, and write `receipts/job.json`.
