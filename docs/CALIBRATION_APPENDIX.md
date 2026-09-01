# Calibration appendix (development evidence)

This appendix reports the confined OpenRouter matrix used to freeze
harness 0.6.0 ranking rules. It is **not** an official StrongOrc
leaderboard.

The models below ran on private bank
`strongorc-frontier-v6-2026-08-31`, commitment
`6a156d8175a0195562e349c5d481552cc2fce43218f7709e4be15369c9a7a449`
([`holdout-0.6.0-openrouter-frontier-v6.json`](../cards/preregister/holdout-0.6.0-openrouter-frontier-v6.json)).
The frozen ranking bank is a later mint of the same design with a new
commitment. See [RANKING.md](RANKING.md). Do not treat these rows as
ranking-v1 scores.

## Why these rows stay labeled

The bank, prompts, scoring headline, and acceptance gates were changed
while watching these outcomes. That is selection. ABC-style reporting
keeps adaptive development separate from a locked evaluation.

Official ranks require a new three-attempt matrix on ranking-v1, after
this repository revision is public, without further bank edits.

## Protocol

- Harness 0.6.0, confined OpenRouter, `examples/openrouter_agent.py`
- 24 tasks, three attempts, `--jobs 2`
- Primary number: `task_equalized_score` (mean per-task strict pass
  rate on non-censored attempts)
- Diagnostic: `task_evidence_score` (protocol-gated hidden evidence)
- Coverage: 1.00 on every system below (no provider refusals in the
  scored matrix)
- Fit: 2PL identified on 9 live systems; 21 items kept, 3 extreme
  items omitted from the IRT step, 0 rewrite/drop
- Report status: `fitted`; `protocol_ready`: true

## Strict pass matrix

| System | Band | Strict pass | Evidence | Tasks passed (first attempt) | USD |
| --- | --- | --- | --- | --- | --- |
| `openai/gpt-5.6-sol` | frontier | 0.694 | 0.883 | 18/24 | 4.53 |
| `anthropic/claude-fable-5` | frontier | 0.667 | 0.869 | 17/24 | 133.24 |
| `google/gemini-3.7-flash` | frontier | 0.583 | 0.895 | 17/24 | 5.43 |
| `deepseek/deepseek-v4-pro` | middle | 0.181 | 0.656 | 4/24 | 4.24 |
| `deepseek/deepseek-v4-flash` | middle | 0.153 | 0.475 | 4/24 | 0.99 |
| `anthropic/claude-haiku-4.5` | weak | 0.139 | 0.584 | 3/24 | 18.19 |
| `mistralai/devstral-2512` | weak | 0.069 | 0.341 | 3/24 | 2.94 |
| `google/gemini-3.1-flash-lite` | weak | 0.014 | 0.055 | 1/24 | 1.72 |
| `openai/gpt-5.4-nano` | floor | 0.000 | 0.141 | 0/24 | 0.46 |

Band labels use the calibration diagnostic split in
`src/strongorc/calibrate.py` (frontier from 0.35). The ranking card
uses a stricter published frontier window of 0.50–0.75. Gemini 3.7
Flash sits in both.

## Adjacent paired deltas

Paired task-clustered bootstrap, 10000 samples, 95% interval.

| Comparison | Mean delta | CI95 | P(first better) |
| --- | --- | --- | --- |
| Sol - Fable | 0.028 | [-0.056, 0.125] | 0.676 |
| Fable - Gemini 3.7 Flash | 0.083 | [-0.083, 0.236] | 0.865 |
| Gemini 3.7 Flash - DeepSeek V4 Pro | 0.403 | [0.236, 0.556] | 1.000 |
| DeepSeek V4 Pro - DeepSeek V4 Flash | 0.028 | [-0.056, 0.111] | 0.786 |
| DeepSeek V4 Flash - Haiku 4.5 | 0.014 | [-0.083, 0.097] | 0.595 |
| Haiku 4.5 - Devstral | 0.069 | [-0.014, 0.153] | 0.961 |
| Devstral - Gemini 3.1 Flash-Lite | 0.056 | [-0.014, 0.153] | 0.913 |
| Gemini 3.1 Flash-Lite - GPT-5.4 Nano | 0.014 | [0.000, 0.042] | 0.818 |

Neighbors inside a band do not clear the pre-registered 0.10 delta.
The frontier cluster separates from the middle cluster. Weak and floor
systems stay below the middle window.

## What this licensed

- Strict pass as the ranking headline. Partial evidence inverted
  perceived strength (high evidence, few finished tasks).
- Provider refusals as coverage, after Anthropic content filters hit
  earlier “probe” / “kill” wording. Neutral wording (“revision”,
  “interruption”) is part of the frozen bank.
- Assignment-sensitive broker contracts, so event vocabulary alone
  cannot pass.
- A fresh ranking mint after the matrix, so official runs are not the
  same files the design was tuned on.

## What it does not license

- Publishing Sol > Fable > Gemini as an official StrongOrc rank
- Claiming Gemini is weaker or stronger than Fable; their paired
  interval covers 0
- Destuping public practice oracles from these rows
- Mixing Cursor SDK, OpenCode Go, or `openrouter-shell` into this
  series
