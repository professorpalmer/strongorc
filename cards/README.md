# Cards

Dated JSON scorecards from `strongorc card`.

A card is earned on this harness only. Do not copy `orch_score` / `leaf_score` into a product `capability_score`. A later overlay may cite `harness_version`, `date`, and this file.

## Registry

[`registry.json`](registry.json) is the authoritative inventory. `registry_status`, `contamination`, `comparable_series`, and `retirement_reason` are fields on that file. They are never inferred from a filename, a slice label, or a high score. `clean` is never the default.

| `registry_status` | Meaning |
| --- | --- |
| `unknown` | Published; not reviewed as clean |
| `leak_diagnostic` | Agent could read this checkout |
| `retired_evidence` | Saturated, superseded, or wrong grain; keep as history |
| `non_model` | Scripted oracle baseline, not a model result |
| `clean` | Explicit confined claim only |

Scripted `scripted-pass*.json` cards are `non_model`. Composer brutal cards from the authoring-machine Cursor SDK are `leak_diagnostic`. `hard` and `frontier` live cards are `retired_evidence`. `reason` scripted cards are development baselines, not a registry series.

Frozen trials live in [`raw/`](raw/). A global `*.jsonl` gitignore would drop them; `!cards/raw/*.jsonl` is the only jsonl exception. Do not unignore `.env`, holdout banks, or secrets. `replicate: true` on a registry entry means CI regrades that raw freeze and compares stable scoring fields, ignoring date and path-only metadata. The 36-task `raw/scripted-pass-ladder.jsonl` does not match the 48-task ladder card.

## Scoring

Harness 0.6.0 public practice cards retain `strongorc_score`, the check-weighted hidden / interrupt / protocol diagnostic multiplied by earned honesty. Private ranking calibration uses task-equalized, protocol-gated hidden outcome evidence; interrupt and protocol checks cannot add rank credit. Layout, easy/sealed grains, task/facet rates, and trial-level orch/leaf/outcome/protocol stay as fingerprints. `--repeats N` writes N records per task and fills `pass_at_1` / `pass_at_k` / `n_attempts`. Quote task-clustered intervals first. Cards from 0.5.x are not comparable to 0.6.0. Quote a number with slice and `harness_version`.

Publish in-house registry cards from `brutal` on harness 0.4.3+ only when the agent cannot see this checkout. `native` is a separate series (orchestration protocol, 96 hidden cases). `examples/openrouter_agent.py` is the confined path. `gemini-3.7-flash-brutal.json` and `openai-gpt-4o-brutal.json` are that channel. `composer-2.5-brutal.json` (Cursor SDK) is a leak diagnostic, not a registry overlay.

Calibration pre-registration lives under [`preregister/`](preregister/). It is not a card. `strongorc calibrate` hashes that file onto the report. `*-0.6.0-openrouter.json` is the confined jail series (default live channel). `reason-0.6.0.json` is the Cursor SDK leak-diagnostic channel. `reason-0.6.0-opencode-go.json` is the Puppetmaster `agentic` + OpenCode Go channel. Live IRT refuses mixed confinement. Do not mix the three. Practice slices are brutal, native, ladder, and reason. Ranking is holdout. core / hard / frontier stay retired evidence.

`scripted-pass.json` is the core-slice oracle-non-vacuity baseline. `scripted-pass-frontier.json` is the same for frontier. `scripted-pass-brutal.json` is the same for brutal. `scripted-pass-native.json` is the same for native. `scripted-pass-ladder.json` is the same for ladder. `scripted-pass-reason.json` is the same for the public development `reason` slice and is not a registry card. None of those are model results. `ladder` is the confined difficulty series (48 tasks, 384 hidden cases; r4 is the inversion ceiling).
