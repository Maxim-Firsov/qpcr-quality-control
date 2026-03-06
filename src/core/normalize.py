"""Normalization helpers for canonical qPCR curve rows."""

from __future__ import annotations

from typing import Iterable


def normalize_well_id(well_id: str) -> str:
    if not well_id:
        return ""
    row = well_id[0].upper()
    col = well_id[1:].strip()
    if not col:
        return well_id.upper()
    if col.isdigit():
        return f"{row}{int(col):02d}"
    return well_id.upper()


def normalize_rows(rows: Iterable[dict]) -> list[dict]:
    normalized: list[dict] = []
    for raw in rows:
        row = dict(raw)
        row["run_id"] = str(row.get("run_id", "") or "run_unknown")
        row["plate_id"] = str(row.get("plate_id", "") or "plate_unknown")
        row["well_id"] = normalize_well_id(str(row.get("well_id", "")))
        row["sample_id"] = str(row.get("sample_id", "") or "unknown_sample")
        row["target_id"] = str(row.get("target_id", "") or "unknown_target")
        row["cycle"] = int(row["cycle"])
        row["fluorescence"] = float(row["fluorescence"])
        row["is_melt_stage"] = bool(row.get("is_melt_stage", False))
        normalized.append(row)
    normalized.sort(
        key=lambda r: (
            r["run_id"],
            r["plate_id"],
            r["well_id"],
            r["target_id"],
            r["cycle"],
        )
    )
    return normalized
