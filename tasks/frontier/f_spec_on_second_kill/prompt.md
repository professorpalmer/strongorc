You are the orchestrator. Convert `src/prep` first, then implement `src/scale` from `job/spec.json`.

Write `state/checkpoint1.json` after prep and `state/checkpoint2.json` after you re-read the spec the first time. If the spec changes later, honor the live file, not memory.

Emit checkpoints and `job_completed`.
