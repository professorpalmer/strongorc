You are the orchestrator. Three waves, in order: `add`, then `mul`, then `scale`. Convert each to typed TypeScript and delete leftover `.js`.

A later wave starts only after that wave's predecessor test exits 0. After a passing wave test, write `.harness/waveN_verified` containing `ok` before starting the next wave.

Emit `worker_started` / `worker_finished` per wave, the wave verify / start events, then `job_completed`, and write `receipts/job.json`.
