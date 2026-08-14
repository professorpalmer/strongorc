You are a leaf worker. `state/discoveries/name.json` already holds the project name.

Write `output/first.txt` and `output/second.txt`, both containing that name and the `nonce` field from the discovery file. You may emit one `llm_call` to notice the artifact. The second lookup must emit `discovery_reused` and must not emit another `llm_call`.
