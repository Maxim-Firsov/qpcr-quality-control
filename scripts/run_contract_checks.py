"""Contract check runner for local hooks and CI."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path


def main() -> int:
    preferred = Path("C:/Users/max/AppData/Roaming/Python/Python313/pytest-tmp")
    base_temp = preferred if preferred.exists() else Path(tempfile.gettempdir()) / "pytest-qpcr-contract"
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/contract",
        "--basetemp",
        str(base_temp),
    ]
    return subprocess.call(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
