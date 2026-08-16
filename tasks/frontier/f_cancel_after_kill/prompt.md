You are the orchestrator. Convert `src/early` then `src/late`.

Checkpoint after `src/early`. If `job/cancel.json` appears, stop. Do not convert `src/late`. Receipt status must be `refused`. Emit `job_refused`, not `job_completed`.
