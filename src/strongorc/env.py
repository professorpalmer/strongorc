from __future__ import annotations

import os

CANONICAL = "STRONGORC_"
LEGACY = "DURABLE_ORCH_"


def getenv(suffix: str, default: str | None = None) -> str | None:
    for prefix in (CANONICAL, LEGACY):
        value = os.environ.get(f"{prefix}{suffix}")
        if value is not None:
            return value
    return default


def require(suffix: str) -> str:
    value = getenv(suffix)
    if value is None:
        raise KeyError(f"set {CANONICAL}{suffix}")
    return value


def export(env: dict[str, str], suffix: str, value: str) -> None:
    env[f"{CANONICAL}{suffix}"] = value
    env[f"{LEGACY}{suffix}"] = value


def bind_run(
    env: dict[str, str],
    *,
    run_dir: str,
    task_id: str,
    track: str,
    model: str,
    prompt: str,
) -> None:
    export(env, "RUN_DIR", run_dir)
    export(env, "TASK_ID", task_id)
    export(env, "TRACK", track)
    export(env, "MODEL", model)
    export(env, "PROMPT", prompt)
