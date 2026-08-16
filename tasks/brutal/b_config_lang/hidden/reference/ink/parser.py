from __future__ import annotations

import re
from pathlib import Path
from typing import Any

INCLUDE = re.compile(r"^\$\{include:(.+)\}$")
INTERPOLATE = re.compile(r"\$\{([A-Za-z0-9_.]+)\}")


def parse(text: str, root: str | Path | None = None, filename: str = "<stdin>") -> dict[str, Any]:
    base = Path(root) if root is not None else Path(".")
    return _parse(text, base, filename, set())


def _parse(text: str, base: Path, filename: str, stack: set[str]) -> dict[str, Any]:
    if filename in stack:
        raise ValueError(f"circular include {filename}")
    stack = set(stack)
    stack.add(filename)
    data: dict[str, Any] = {}
    section = ""
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1].strip()
            continue
        include = INCLUDE.match(line)
        if include:
            rel = include.group(1).strip()
            path = (base / rel).resolve()
            nested = _parse(path.read_text(encoding="utf-8"), path.parent, str(path), stack)
            data.update(nested)
            continue
        if "=" not in line:
            raise ValueError(f"bad line {raw!r}")
        key, value = line.split("=", 1)
        key = key.strip()
        if section:
            key = f"{section}.{key}"
        data[key] = _coerce(_expand(value.strip(), data))
    return data


def _expand(value: str, data: dict[str, Any]) -> str:
    def repl(match: re.Match[str]) -> str:
        return str(data.get(match.group(1), match.group(0)))

    return INTERPOLATE.sub(repl, value)


def _coerce(value: str) -> Any:
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    if value in {"true", "false"}:
        return value == "true"
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    return value
