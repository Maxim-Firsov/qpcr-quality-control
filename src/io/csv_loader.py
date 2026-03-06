"""CSV loading utilities."""

from __future__ import annotations

import csv
from pathlib import Path


def load_curve_csv(path: str | Path) -> list[dict]:
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return [dict(row) for row in reader]


def load_plate_meta_csv(path: str | Path) -> dict[tuple[str, str], dict]:
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        out: dict[tuple[str, str], dict] = {}
        for row in reader:
            out[(row["plate_id"], row["well_id"])] = dict(row)
        return out
