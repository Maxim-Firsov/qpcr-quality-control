"""QC decision layer applied above inferred state paths."""

from __future__ import annotations

import json
from collections import defaultdict
from statistics import mean
from typing import Iterable

from src.core.plate_layout import is_edge_well, resolve_plate_shape

LATE_CT_THRESHOLD = 35.0
LOW_SIGNAL_THRESHOLD = 0.15


def _compact_state_path(states: list[str]) -> str:
    if not states:
        return ""
    out: list[str] = []
    current = states[0]
    count = 1
    for state in states[1:]:
        if state == current:
            count += 1
            continue
        out.append(f"{current}:{count}")
        current = state
        count = 1
    out.append(f"{current}:{count}")
    return "|".join(out)


def _estimate_ct(rows: list[dict], amplified: bool) -> float | None:
    if not amplified:
        return None

    max_signal = max(float(row.get("f_adj", 0.0)) for row in rows)
    threshold = max(0.2, max_signal * 0.35)
    previous_signal = float(rows[0].get("f_adj", 0.0))
    previous_cycle = float(rows[0]["cycle"])
    for row in rows[1:]:
        signal = float(row.get("f_adj", 0.0))
        cycle = float(row["cycle"])
        if signal >= threshold and previous_signal < threshold:
            signal_delta = signal - previous_signal
            if signal_delta <= 0:
                return cycle
            cycle_fraction = (threshold - previous_signal) / signal_delta
            return round(previous_cycle + cycle_fraction, 3)
        previous_signal = signal
        previous_cycle = cycle

    for row in rows:
        if row["state"] == "exponential_amplification":
            return float(row["cycle"])
    return None


def apply_qc_rules(
    inferred_rows: Iterable[dict],
    plate_meta: dict[tuple[str, str], dict] | None = None,
    confidence_threshold: float = 0.6,
    plate_schema: str = "auto",
) -> list[dict]:
    plate_meta = plate_meta or {}
    grouped: dict[tuple[str, str, str, str], list[dict]] = defaultdict(list)
    for row in inferred_rows:
        key = (row["run_id"], row["plate_id"], row["well_id"], row["target_id"])
        grouped[key].append(row)

    plate_shapes: dict[str, tuple[int, int]] = defaultdict(tuple)
    plate_wells: dict[str, set[str]] = defaultdict(set)
    for _, plate_id, well_id, _ in grouped.keys():
        plate_wells[plate_id].add(well_id)
    for plate_id, well_ids in plate_wells.items():
        plate_shapes[plate_id] = resolve_plate_shape(well_ids, plate_schema=plate_schema)

    calls: list[dict] = []
    for key, rows in grouped.items():
        run_id, plate_id, well_id, target_id = key
        rows = sorted(rows, key=lambda r: r["cycle"])
        plate_shape = plate_shapes[plate_id]
        states = [r["state"] for r in rows]
        confidences = [float(r["state_confidence"]) for r in rows]
        avg_conf = mean(confidences) if confidences else 0.0
        metadata = plate_meta.get((plate_id, well_id), {})
        control_type = metadata.get("control_type", "sample")
        sample_id = rows[0].get("sample_id", "unknown_sample")
        max_signal = max(float(row.get("f_adj", 0.0)) for row in rows)

        amplified = any(state == "exponential_amplification" for state in states)
        flags: list[str] = []
        if amplified and control_type == "ntc":
            flags.append("ntc_contamination")
        if avg_conf < confidence_threshold:
            flags.append("low_confidence")
        if max_signal < LOW_SIGNAL_THRESHOLD:
            flags.append("low_signal_curve")

        if amplified and "low_confidence" not in flags:
            call_label = "amplified"
        elif amplified:
            call_label = "ambiguous"
        else:
            call_label = "not_amplified"

        ct_estimate = _estimate_ct(rows, amplified=amplified)
        if ct_estimate is not None and ct_estimate >= LATE_CT_THRESHOLD:
            flags.append("late_amplification")
        if control_type == "positive_control" and call_label != "amplified":
            flags.append("positive_control_failure")
        if is_edge_well(well_id, plate_shape) and ("late_amplification" in flags or "low_confidence" in flags):
            flags.append("edge_well_review")

        confidence = avg_conf
        if amplified and ct_estimate is not None and ct_estimate < LATE_CT_THRESHOLD:
            confidence += 0.05
        if "late_amplification" in flags:
            confidence -= 0.15
        if "low_signal_curve" in flags:
            confidence -= 0.1
        confidence = round(min(1.0, max(0.0, confidence)), 3)

        calls.append(
            {
                "run_id": run_id,
                "plate_id": plate_id,
                "well_id": well_id,
                "sample_id": sample_id,
                "target_id": target_id,
                "control_type": control_type,
                "ct_estimate": ct_estimate,
                "hmm_state_path_compact": _compact_state_path(states),
                "amplification_confidence": confidence,
                "call_label": call_label,
                "qc_status": "pass",
                "qc_flags": json.dumps(flags),
                "replicate_group": metadata.get("replicate_group", ""),
            }
        )

    # Replicate-discordance check is applied after first-pass labels are assigned.
    replicate_groups: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    for call in calls:
        if call["control_type"] != "sample":
            continue
        replicate_group = str(call.get("replicate_group", "")).strip()
        if not replicate_group:
            continue
        key = (call["plate_id"], call["target_id"], replicate_group)
        replicate_groups[key].append(call)

    for _, group in replicate_groups.items():
        labels = {call["call_label"] for call in group}
        if len(group) < 2 or len(labels) <= 1:
            continue
        for call in group:
            flags = json.loads(call["qc_flags"])
            if "replicate_discordance" not in flags:
                flags.append("replicate_discordance")
            call["qc_flags"] = json.dumps(flags)

    for call in calls:
        flags = json.loads(call["qc_flags"])
        if (
            "ntc_contamination" in flags
            or "replicate_discordance" in flags
            or "positive_control_failure" in flags
        ):
            call["qc_status"] = "rerun"
        elif "late_amplification" in flags or "low_confidence" in flags or "edge_well_review" in flags or "low_signal_curve" in flags:
            call["qc_status"] = "review"
        else:
            call["qc_status"] = "pass"
        call.pop("replicate_group", None)

    calls.sort(key=lambda r: (r["run_id"], r["plate_id"], r["well_id"], r["target_id"]))
    return calls
