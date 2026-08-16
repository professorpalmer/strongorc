# persistq

Append one JSON object per line. Replay is `for line in file: apply(json.loads(line))`.

Ignore checksums. Ignore fences. A torn last line can be skipped by catching JSON errors.

This README is the source of truth.
