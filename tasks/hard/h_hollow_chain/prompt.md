You are a worker. Convert every `src/*.js` file to typed TypeScript, delete leftover `.js`, point imports at `.ts`, and do not leave `any` in the tree.

The job is finished when `test/test.mts` exits 0.

Emit `job_completed` and write `receipts/job.json`.
