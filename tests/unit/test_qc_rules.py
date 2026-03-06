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


def test_qc_rules_flags_replicate_discordance_for_group():
    inferred = [
        {
            "run_id": "r1",
            "plate_id": "p1",
            "well_id": "A02",
            "sample_id": "s_rep1",
            "target_id": "t1",
            "cycle": 1,
            "state": "baseline_noise",
            "state_confidence": 0.95,
        },
        {
            "run_id": "r1",
            "plate_id": "p1",
            "well_id": "A03",
            "sample_id": "s_rep2",
            "target_id": "t1",
            "cycle": 1,
            "state": "exponential_amplification",
            "state_confidence": 0.95,
        },
    ]
    meta = {
        ("p1", "A02"): {"control_type": "sample", "replicate_group": "rg1"},
        ("p1", "A03"): {"control_type": "sample", "replicate_group": "rg1"},
    }
    calls = apply_qc_rules(inferred, plate_meta=meta)
    assert len(calls) == 2
    for call in calls:
        assert call["qc_status"] == "rerun"
        assert "replicate_discordance" in json.loads(call["qc_flags"])
