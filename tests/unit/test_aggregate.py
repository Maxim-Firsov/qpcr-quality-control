import json

from src.core.aggregate import summarize_plates


def test_summarize_plates_counts_statuses():
    calls = [
        {
            "plate_id": "p1",
            "qc_status": "pass",
            "qc_flags": json.dumps([]),
        },
        {
            "plate_id": "p1",
            "qc_status": "rerun",
            "qc_flags": json.dumps(["ntc_contamination"]),
        },
    ]
    summary = summarize_plates(calls)
    assert summary["global_counts"]["pass"] == 1
    assert summary["global_counts"]["rerun"] == 1
    assert summary["plates"][0]["ntc_contamination_count"] == 1
