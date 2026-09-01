#!/usr/bin/env python3
"""Keyless replication: validate cards/registry.json and regrade scripted cards.

Stdlib plus the StrongOrc install. No API keys. Does not set STRONGORC_HOLDOUT.
Compares stable scoring fields and ignores date / path-only metadata.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from strongorc.registry import replicate  # noqa: E402


def main() -> int:
    errors = replicate(ROOT)
    if errors:
        print("replicate failed:", file=sys.stderr)
        for item in errors:
            print(f"  {item}", file=sys.stderr)
        return 1
    print("registry ok; scripted card regrade matches stable scoring fields")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
