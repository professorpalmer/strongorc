# Holdout slice

Private paper / saturation items. Real banks are **never** committed here.

Public `tasks/holdout` contains only this README. Do not commit task ids,
metadata, prompts, authoring scripts, gold agents, oracles, generators,
worker pools, hidden cases, references, or expected values.

## Operator contract

1. Keep the overlay **outside this repository**. Point `STRONGORC_HOLDOUT`
   (legacy `DURABLE_ORCH_HOLDOUT`) at that root. Gitignores `.holdout/`,
   `.strongorc-holdout/`, and `/holdout-overlay/` for local copies.
2. Overlay task directories are opaque ids `hld_<hex>`. Orchestrator tasks
   include a private `workers.py` pool reached only through the harness
   broker. Worker tasks receive a frozen orchestrator assignment.
3. Generators are trusted grader-side code (stdlib-only, loaded
   in-process — not a sandbox). They implement
   `materialize(run_dir, nonce)` for candidate-visible live evidence,
   optional `after_interrupt(run_dir, nonce, step_index)` for sealed
   revisions, and `generate(run_dir, nonce) -> pathlib.Path` for hidden
   grade cases. Grade hashes the overlay around each call and jails the
   returned path inside the grading workspace. Overlay mutation or an
   escaped path fails closed. Check names are `case_<hmac8>`.
4. When `STRONGORC_HOLDOUT` is unset, the public slice is empty.
   `strongorc run --slice holdout` and `strongorc card --slice holdout`
   refuse rather than scoring vacuously.
5. Ranking uses the confined OpenRouter jail. Shell is an ablation, never
   the official channel. Do not publish private instances on cards.

Architecture tests use `tests/fixtures/holdout_overlay`, which is a
non-secret miniature overlay — not the private holdout.
