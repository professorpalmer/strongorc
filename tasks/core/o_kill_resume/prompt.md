You are the orchestrator. Do not write layer outputs yourself.

The job has three layers listed in `job/layers.json`. After layer 1, your process will be killed. Persist a checkpoint, resume from it, and finish layers 2 and 3.

Write `state/checkpoint.json` before the kill. After resume, write `output/done.txt` containing each layer id on its own line, in order.

Emit `checkpoint_written`, `resumed_from_checkpoint`, `worker_started`, `worker_finished`, and `job_completed`. Write `receipts/job.json`.
