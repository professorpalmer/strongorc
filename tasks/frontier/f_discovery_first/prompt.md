You are the orchestrator. Read `job/spec.json`, write `state/discoveries/scale.json` with the live factor, emit `discovery_materialized`, then start a worker to implement `src/scale.ts`.

A worker that starts before the discovery is a protocol fail.

Emit `job_completed`.
