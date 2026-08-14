You are the orchestrator. Convert every `src/layer1|2|3/*.js` file to TypeScript with explicit `number` types, then delete the `.js` sources. Imports must point at `.ts`.

The job has three layers in `job/layers.json`. After layer 1 is converted, write `state/checkpoint.json` with `last_completed: "layer1"`. Then wait. Do not exit and do not start layers 2 or 3. The harness SIGKILLs this process, then respawns you with `STRONGORC_RESUME=1`. Resume from the checkpoint. Do not redo layer 1. Convert layers 2 and 3 after resume.

Do not write the conversions yourself if you are only planning — dispatch a worker. Emit `checkpoint_written`, `resumed_from_checkpoint`, `worker_started`, `worker_finished`, and `job_completed`. Write `receipts/job.json`.
