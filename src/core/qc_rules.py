"""QC decision layer applied above inferred state paths."""

from __future__ import annotations

import json
from collections import defaultdict
from statistics import mean
from typing import Iterable


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


def apply_qc_rules(
    inferred_rows: Iterable[dict],
    plate_meta: dict[tuple[str, str], dict] | None = None,
    confidence_threshold: float = 0.6,
) -> list[dict]:
    plate_meta = plate_meta or {}
    grouped: dict[tuple[str, str, str, str], list[dict]] = defaultdict(list)
    for row in inferred_rows:
        key = (row["run_id"], row["plate_id"], row["well_id"], row["target_id"])
        grouped[key].append(row)

    calls: list[dict] = []
    for key, rows in grouped.items():
        run_id, plate_id, well_id, target_id = key
        rows = sorted(rows, key=lambda r: r["cycle"])
        states = [r["state"] for r in rows]
        confidences = [float(r["state_confidence"]) for r in rows]
        avg_conf = mean(confidences) if confidences else 0.0
        metadata = plate_meta.get((plate_id, well_id), {})
        control_type = metadata.get("control_type", "sample")
        sample_id = rows[0].get("sample_id", "unknown_sample")

        amplified = any(state == "exponential_amplification" for state in states)
        flags: list[str] = []
        if amplified and control_type == "ntc":
            flags.append("ntc_contamination")
        if avg_conf < confidence_threshold:
            flags.append("low_confidence")

        if amplified and "low_confidence" not in flags:
            call_label = "amplified"
        elif amplified:
            call_label = "ambiguous"
        else:
            call_label = "not_amplified"

        ct_estimate = None
        for row in rows:
            if row["state"] == "exponential_amplification":
                ct_estimate = row["cycle"]
                break

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
                "amplification_confidence": round(avg_conf, 3),
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
        if "ntc_contamination" in flags or "replicate_discordance" in flags:
            call["qc_status"] = "rerun"
        elif flags:
            call["qc_status"] = "review"
        else:
            call["qc_status"] = "pass"
        call.pop("replicate_group", None)

    calls.sort(key=lambda r: (r["run_id"], r["plate_id"], r["well_id"], r["target_id"]))
    return calls
