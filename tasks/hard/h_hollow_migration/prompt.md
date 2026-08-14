You are a worker. Convert every `src/*.js` file to TypeScript with explicit `number` types. Delete the `.js` sources. Point imports at `.ts`. Do not use `any`.

`test/test.mts` is the hidden check. The oracle re-runs it with `node --experimental-strip-types`. A leftover `.js` beside a `.ts` is a hollow pass.

Emit `job_completed` and write `receipts/job.json`.
