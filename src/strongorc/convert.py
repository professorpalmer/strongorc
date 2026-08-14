from __future__ import annotations

import re
from pathlib import Path

_FN = re.compile(r"export function (\w+)\(([^)]*)\)")
_IMPORT = re.compile(r'''from (['"])((?:\.\.?/)+[^'"]+)\.js\1''')


def _typed_params(params: str) -> str:
    parts = [part.strip() for part in params.split(",") if part.strip()]
    return ", ".join(f"{part}: number" for part in parts)


def js_to_typed_ts(source: str) -> str:
    def replace(match: re.Match[str]) -> str:
        return f"export function {match.group(1)}({_typed_params(match.group(2))}): number"

    typed = _FN.sub(replace, source)
    return _IMPORT.sub(r"from \1\2.ts\1", typed)


def convert_js_tree(root: Path) -> list[Path]:
    written: list[Path] = []
    for js_path in sorted(root.rglob("*.js")):
        ts_path = js_path.with_suffix(".ts")
        ts_path.write_text(js_to_typed_ts(js_path.read_text(encoding="utf-8")), encoding="utf-8")
        js_path.unlink()
        written.append(ts_path)
    return written
