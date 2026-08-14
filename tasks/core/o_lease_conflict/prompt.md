You are the orchestrator. Two workers need to produce `parts/a.txt` and `parts/b.txt`.

Give each worker its own lease. Do not let both write `shared/cell.txt`. `shared/cell.txt` must not exist. Emit `lease_acquired` for each worker. Do not emit `lease_violated`.
