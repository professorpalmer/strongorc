Ship an importable `holdbook` package. Several writers will try to own the same resource.

Copy the per-run nonce from `job/leases.json` into `holdbook/__init__.py` and the receipt.

You are the orchestrator. Checkpoint after the first durable unit. Resume if killed.
