"""Feature transforms for HMM inference."""

from __future__ import annotations

from collections import defaultdict
from typing import Iterable


def build_features(rows: Iterable[dict]) -> list[dict]:
    grouped: dict[tuple[str, str, str, str], list[dict]] = defaultdict(list)
    for row in rows:
        key = (row["run_id"], row["plate_id"], row["well_id"], row["target_id"])
        grouped[key].append(row)

    out: list[dict] = []
    for key, group in grouped.items():
        ordered = sorted(group, key=lambda r: r["cycle"])
        baseline = min(r["fluorescence"] for r in ordered)
        prev_df = 0.0
        prev_f = None
        for row in ordered:
            adj = row["fluorescence"] - baseline
            if prev_f is None:
                df = 0.0
            else:
                df = row["fluorescence"] - prev_f
            d2f = df - prev_df
            prev_df = df
            prev_f = row["fluorescence"]
            feature_row = dict(row)
            feature_row["f_adj"] = adj
            feature_row["df"] = df
            feature_row["d2f"] = d2f
            out.append(feature_row)
    out.sort(
        key=lambda r: (
            r["run_id"],
            r["plate_id"],
            r["well_id"],
            r["target_id"],
            r["cycle"],
        )
    )
    return out
