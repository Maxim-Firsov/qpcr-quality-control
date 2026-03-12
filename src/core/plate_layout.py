"""Plate geometry helpers for edge-aware QC logic."""

from __future__ import annotations

from typing import Iterable


def _row_index(well_id: str) -> int:
    return ord(well_id[0].upper()) - ord("A") + 1


def _col_index(well_id: str) -> int:
    return int(well_id[1:])


def resolve_plate_shape(well_ids: Iterable[str], plate_schema: str = "auto") -> tuple[int, int]:
    schema = str(plate_schema or "auto").lower()
    if schema == "96":
        return (8, 12)
    if schema == "384":
        return (16, 24)

    observed = [well_id for well_id in well_ids if len(well_id) >= 2]
    if not observed:
        return (8, 12)

    max_row = max(_row_index(well_id) for well_id in observed)
    max_col = max(_col_index(well_id) for well_id in observed)
    if max_row <= 8 and max_col <= 12:
        return (8, 12)
    if max_row <= 16 and max_col <= 24:
        return (16, 24)
    return (max_row, max_col)


def is_edge_well(well_id: str, plate_shape: tuple[int, int]) -> bool:
    if len(well_id) < 2:
        return False
    try:
        row_index = _row_index(well_id)
        col_index = _col_index(well_id)
    except ValueError:
        return False

    row_count, col_count = plate_shape
    return row_index in {1, row_count} or col_index in {1, col_count}
