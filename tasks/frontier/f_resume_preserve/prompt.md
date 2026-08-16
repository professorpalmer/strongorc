You are a worker resuming a job. `state/checkpoint.json` says `layer1` is done.

Leave `src/layer1/keep.ts` byte-identical. Convert `src/layer2` only. Emit `resumed_from_checkpoint` and `job_completed`.
