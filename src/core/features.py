"""Feature transforms for HMM inference."""

from __future__ import annotations

from collections import defaultdict
from statistics import mean, median
from typing import Iterable

from src.core.normalization_profiles import load_normalization_profiles, resolve_normalization_profile


def _baseline_value(ordered: list[dict], baseline_strategy: str, baseline_cycle_count: int) -> float:
    values = [float(row["fluorescence"]) for row in ordered[: max(1, baseline_cycle_count)]]
    if baseline_strategy == "mean_first_n":
        return mean(values)
    if baseline_strategy == "median_first_n":
        return median(values)
    return min(float(row["fluorescence"]) for row in ordered)


def build_features(
    rows: Iterable[dict],
    normalization_profiles: dict | None = None,
    requested_profile: str | None = None,
) -> list[dict]:
    normalization_profiles = normalization_profiles or load_normalization_profiles()
    grouped: dict[tuple[str, str, str, str], list[dict]] = defaultdict(list)
    for row in rows:
        key = (row["run_id"], row["plate_id"], row["well_id"], row["target_id"])
        grouped[key].append(row)

    out: list[dict] = []
    for key, group in grouped.items():
        ordered = sorted(group, key=lambda r: r["cycle"])
        profile = resolve_normalization_profile(
            instrument=ordered[0].get("instrument", "unknown_instrument"),
            target_id=ordered[0].get("target_id", "unknown_target"),
            profiles=normalization_profiles,
            requested_profile=requested_profile,
        )
        baseline_strategy = str(profile.get("baseline_strategy", "minimum"))
        baseline_cycle_count = int(profile.get("baseline_cycle_count", 3))
        signal_scale = float(profile.get("signal_scale", 1.0))
        # Baseline anchoring stays deterministic while allowing assay/instrument-specific profiles.
        baseline = _baseline_value(ordered, baseline_strategy=baseline_strategy, baseline_cycle_count=baseline_cycle_count)
        prev_df = 0.0
        prev_f = None
        for row in ordered:
            adj = (float(row["fluorescence"]) - baseline) * signal_scale
            if prev_f is None:
                df = 0.0
            else:
                df = (float(row["fluorescence"]) - prev_f) * signal_scale
            d2f = df - prev_df
            prev_df = df
            prev_f = float(row["fluorescence"])
            feature_row = dict(row)
            feature_row["f_adj"] = adj
            feature_row["df"] = df
            feature_row["d2f"] = d2f
            feature_row["baseline_value"] = round(baseline, 6)
            feature_row["baseline_strategy"] = baseline_strategy
            feature_row["normalization_profile"] = profile["profile_name"]
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
