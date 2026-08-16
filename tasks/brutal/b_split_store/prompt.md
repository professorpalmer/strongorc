Two importable packages: `binbox` and `namemap`.

Read `job/leases.json` and `job/budget.json` every time you wake. Those files change. Do not write an unleased package. Do not start more workers than `max_workers`.

You are the orchestrator. Checkpoint after the first leased package.
