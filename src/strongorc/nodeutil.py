from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def node_bin() -> str:
    found = shutil.which("node")
    if not found:
        raise FileNotFoundError("node is required to grade the hard slice")
    return found


def run_node_test(run_dir: Path, relative: str, timeout: int = 30) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [node_bin(), "--experimental-strip-types", "--no-warnings", str(run_dir / relative)],
        cwd=run_dir,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
