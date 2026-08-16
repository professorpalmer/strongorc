You are the orchestrator. Convert a tree only while it is leased.

Checkpoint after the first leased tree. Re-read `job/leases.json` after any interrupt. Convert every tree that is or was leased during this job. Do not invent a shared CONFLICT file.

Emit `lease_acquired` per worker and `job_completed`.
