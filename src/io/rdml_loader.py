"""RDML ingest placeholder.

The v0.1.0 scaffold runs in canonical CSV mode for deterministic tests.
"""

from __future__ import annotations

from pathlib import Path


def load_rdml(path: str | Path) -> list[dict]:
    raise NotImplementedError(f"RDML mode not implemented in scaffold: {path}")
