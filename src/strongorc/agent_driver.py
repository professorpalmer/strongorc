from __future__ import annotations

import runpy
from pathlib import Path

from strongorc.env import require


def main() -> None:
    runpy.run_path(
        require("AGENT"),
        init_globals={
            "RUN_DIR": Path(require("RUN_DIR")),
            "MODEL": require("MODEL"),
            "TASK_ID": require("TASK_ID"),
        },
    )


if __name__ == "__main__":
    main()
