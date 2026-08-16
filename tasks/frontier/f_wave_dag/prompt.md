You are the orchestrator. Four files: `src/a.js`, `src/b.js`, `src/c.js`, `src/d.js`.

Wave A must pass `test/wave_a.mts` and write `.harness/wave_a_verified` before B or C start. B and C may run after A. D starts only after both B and C have verified.

Emit `wave_verified` (A), `wave2_started`/`wave2_verified` (B), `wave3_started`/`wave3_verified` (C), then convert D and `job_completed`.
