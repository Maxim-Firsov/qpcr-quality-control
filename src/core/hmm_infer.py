"""Deterministic HMM-like inference scaffold."""

from __future__ import annotations

from collections import defaultdict
from typing import Iterable

STATE_BASELINE = "baseline_noise"
STATE_EXP = "exponential_amplification"
STATE_TRANSITION = "linear_transition"
STATE_PLATEAU = "plateau"


def _state_from_features(feature_row: dict, exp_df_threshold: float, plateau_df_threshold: float) -> str:
    df = float(feature_row["df"])
    d2f = float(feature_row["d2f"])
    if df >= exp_df_threshold and d2f >= 0:
        return STATE_EXP
    if df >= plateau_df_threshold:
        return STATE_TRANSITION
    if df >= 0 and d2f < 0:
        return STATE_PLATEAU
    return STATE_BASELINE


def infer_state_paths(
    feature_rows: Iterable[dict],
    exp_df_threshold: float = 0.12,
    plateau_df_threshold: float = 0.03,
) -> list[dict]:
    grouped: dict[tuple[str, str, str, str], list[dict]] = defaultdict(list)
    for row in feature_rows:
        key = (row["run_id"], row["plate_id"], row["well_id"], row["target_id"])
        grouped[key].append(row)

    inferred: list[dict] = []
    for _, rows in grouped.items():
        for row in sorted(rows, key=lambda r: r["cycle"]):
            state = _state_from_features(row, exp_df_threshold, plateau_df_threshold)
            out = dict(row)
            out["state"] = state
            # Confidence is deterministic and bounded for simple contract testing.
            out["state_confidence"] = min(1.0, max(0.0, abs(float(row["df"])) * 2.0))
            inferred.append(out)
    inferred.sort(
        key=lambda r: (
            r["run_id"],
            r["plate_id"],
            r["well_id"],
            r["target_id"],
            r["cycle"],
        )
    )
    return inferred
