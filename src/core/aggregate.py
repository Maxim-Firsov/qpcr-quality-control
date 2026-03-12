"""Plate-level summary aggregation."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from typing import Iterable

from src.core.plate_layout import is_edge_well, resolve_plate_shape


def summarize_plates(well_calls: Iterable[dict], generated_at_utc: str, plate_schema: str = "auto") -> dict:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for call in well_calls:
        grouped[call["plate_id"]].append(call)

    plates = []
    global_counts = Counter()
    for plate_id, calls in grouped.items():
        plate_shape = resolve_plate_shape((call["well_id"] for call in calls), plate_schema=plate_schema)
        status_counts = Counter(call["qc_status"] for call in calls)
        ntc_contam = 0
        replicate_discordance = 0
        flagged_edge_wells = 0
        flagged_non_edge_wells = 0
        total_edge_wells = 0
        total_non_edge_wells = 0
        for call in calls:
            # Flag totals are surfaced for report-level rerun rationale.
            flags = json.loads(call["qc_flags"])
            ntc_contam += int("ntc_contamination" in flags)
            replicate_discordance += int("replicate_discordance" in flags)
            is_edge = is_edge_well(call["well_id"], plate_shape)
            if is_edge:
                total_edge_wells += 1
                flagged_edge_wells += int(call["qc_status"] != "pass")
            else:
                total_non_edge_wells += 1
                flagged_non_edge_wells += int(call["qc_status"] != "pass")
        plate_status = "pass"
        if status_counts["rerun"] > 0:
            plate_status = "rerun"
        elif status_counts["review"] > 0:
            plate_status = "review"

        edge_rate = flagged_edge_wells / total_edge_wells if total_edge_wells else 0.0
        non_edge_rate = flagged_non_edge_wells / total_non_edge_wells if total_non_edge_wells else 0.0

        plate_summary = {
            "plate_id": plate_id,
            "well_total": len(calls),
            "pass_count": status_counts["pass"],
            "review_count": status_counts["review"],
            "rerun_count": status_counts["rerun"],
            "ntc_contamination_count": ntc_contam,
            "replicate_discordance_count": replicate_discordance,
            "edge_effect_alert": flagged_edge_wells >= 2 and edge_rate > non_edge_rate,
            "plate_status": plate_status,
        }
        plates.append(plate_summary)
        global_counts.update(status_counts)

    plates.sort(key=lambda p: p["plate_id"])
    return {
        "schema_version": "v0.1.0",
        "generated_at_utc": generated_at_utc,
        "plates": plates,
        "global_counts": {
            "pass": global_counts["pass"],
            "review": global_counts["review"],
            "rerun": global_counts["rerun"],
        },
    }
