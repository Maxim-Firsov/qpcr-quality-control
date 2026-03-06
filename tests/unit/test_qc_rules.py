import json

from src.core.qc_rules import apply_qc_rules


def test_qc_rules_flags_ntc_contamination():
    inferred = [
        {
            "run_id": "r1",
            "plate_id": "p1",
            "well_id": "A01",
            "sample_id": "s1",
            "target_id": "t1",
            "cycle": 1,
            "state": "baseline_noise",
            "state_confidence": 0.9,
        },
        {
            "run_id": "r1",
            "plate_id": "p1",
            "well_id": "A01",
            "sample_id": "s1",
            "target_id": "t1",
            "cycle": 2,
            "state": "exponential_amplification",
            "state_confidence": 0.9,
        },
    ]
    meta = {("p1", "A01"): {"control_type": "ntc"}}
    calls = apply_qc_rules(inferred, plate_meta=meta)
    assert calls[0]["qc_status"] == "rerun"
    assert "ntc_contamination" in json.loads(calls[0]["qc_flags"])
