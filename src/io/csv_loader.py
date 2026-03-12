"""CSV loading utilities."""

from __future__ import annotations

import csv
from pathlib import Path

from src.core.normalize import normalize_well_id


def load_curve_csv(path: str | Path) -> list[dict]:
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return [dict(row) for row in reader]


def load_plate_meta_csv(path: str | Path) -> dict[tuple[str, str], dict]:
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        out: dict[tuple[str, str], dict] = {}
        for row in reader:
            normalized = dict(row)
            normalized["well_id"] = normalize_well_id(str(row["well_id"]))
            out[(row["plate_id"], normalized["well_id"])] = normalized
        return out
