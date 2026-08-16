You are the orchestrator. Convert `src/left` and `src/right` to TypeScript.

Write `state/started.json` after you begin. Durable state may lie. Trust the files under `src/`, not a checkpoint that claims the job is done.

Emit `job_completed` only after both trees are typed and leftover `.js` is gone.
