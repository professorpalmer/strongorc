You are the orchestrator. `job/leases.json` has a fence token. Convert `src/work` to TypeScript and copy the live fence token into `src/work/fence.ts` as `export const FENCE = "<token>"`.

Checkpoint after you read the first table. If interrupted, re-read the token. A stale fence is a fail.

Emit `lease_acquired`, `job_completed`, and a receipt.
