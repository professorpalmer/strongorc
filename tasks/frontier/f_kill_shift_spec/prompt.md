You are the orchestrator. Convert only leased trees. Read `job/leases.json` and `job/spec.json` before you write TypeScript.

Checkpoint after the first leased tree. If the job is interrupted, re-read both files. Do not replay the first prompt from memory.

Emit `lease_acquired`, `checkpoint_written`, `resumed_from_checkpoint` as appropriate, then `job_completed`.
