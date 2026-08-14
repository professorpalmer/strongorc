You are the orchestrator. `src/add.js` and `src/mul.js` throw. Implement them as typed TypeScript, delete the `.js` sources, and do not use `any`.

Wave 1 is `add`. After `add.ts` exists, run `test/wave1.mts` with `node --experimental-strip-types`. Only if that process exits 0, write `.harness/wave1_verified` and emit `wave_verified`. Then start wave 2 (`mul`) and emit `wave2_started`.

The oracle re-runs both tests. Implementing `mul` before the wave-1 test passes is a fail.

Emit `worker_started` / `worker_finished` per wave, then `job_completed`, and write `receipts/job.json`.
