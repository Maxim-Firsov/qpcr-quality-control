"""Validation of canonical curve rows."""

from __future__ import annotations

from collections import defaultdict
from math import isfinite
from typing import Iterable


def _known_well_id(well_id: str) -> bool:
    if len(well_id) < 2:
        return False
    row = well_id[0]
    col = well_id[1:]
    return row.isalpha() and col.isdigit()


def validate_rows(rows: Iterable[dict], min_cycles: int = 25) -> tuple[list[dict], list[dict], dict]:
    eligible: list[dict] = []
    rejected: list[dict] = []
    errors: dict[str, int] = defaultdict(int)
    grouped_cycles: dict[tuple[str, str, str, str], list[int]] = defaultdict(list)

    staged = list(rows)
    for row in staged:
        key = (row["run_id"], row["plate_id"], row["well_id"], row["target_id"])
        grouped_cycles[key].append(row["cycle"])

        valid = True
        if not _known_well_id(row["well_id"]):
            errors["invalid_well_id"] += 1
            valid = False
        if not isfinite(row["fluorescence"]):
            errors["non_finite_fluorescence"] += 1
            valid = False

        if valid:
            eligible.append(row)
        else:
            bad = dict(row)
            bad["reject_reason"] = "field_validation_failed"
            rejected.append(bad)

    min_cycle_failures = set()
    order_failures = set()
    for key, cycles in grouped_cycles.items():
        if len(cycles) < min_cycles:
            min_cycle_failures.add(key)
        if sorted(cycles) != cycles or len(set(cycles)) != len(cycles):
            order_failures.add(key)

    filtered: list[dict] = []
    for row in eligible:
        key = (row["run_id"], row["plate_id"], row["well_id"], row["target_id"])
        if key in min_cycle_failures:
            errors["min_cycles_failed"] += 1
            bad = dict(row)
            bad["reject_reason"] = "min_cycles_failed"
            rejected.append(bad)
            continue
        if key in order_failures:
            errors["cycle_order_failed"] += 1
            bad = dict(row)
            bad["reject_reason"] = "cycle_order_failed"
            rejected.append(bad)
            continue
        filtered.append(row)

    summary = {
        "eligible_rows": len(filtered),
        "rejected_rows": len(rejected),
        "error_counts": dict(errors),
    }
    return filtered, rejected, summary
