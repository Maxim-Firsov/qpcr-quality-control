"""Plate-level summary aggregation."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from typing import Iterable


def summarize_plates(well_calls: Iterable[dict], generated_at_utc: str) -> dict:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for call in well_calls:
        grouped[call["plate_id"]].append(call)

    plates = []
    global_counts = Counter()
    for plate_id, calls in grouped.items():
        status_counts = Counter(call["qc_status"] for call in calls)
        ntc_contam = 0
        replicate_discordance = 0
        for call in calls:
            # Flag totals are surfaced for report-level rerun rationale.
            flags = json.loads(call["qc_flags"])
            ntc_contam += int("ntc_contamination" in flags)
            replicate_discordance += int("replicate_discordance" in flags)
        plate_status = "pass"
        if status_counts["rerun"] > 0:
            plate_status = "rerun"
        elif status_counts["review"] > 0:
            plate_status = "review"

        plate_summary = {
            "plate_id": plate_id,
            "well_total": len(calls),
            "pass_count": status_counts["pass"],
            "review_count": status_counts["review"],
            "rerun_count": status_counts["rerun"],
            "ntc_contamination_count": ntc_contam,
            "replicate_discordance_count": replicate_discordance,
            "edge_effect_alert": False,
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
