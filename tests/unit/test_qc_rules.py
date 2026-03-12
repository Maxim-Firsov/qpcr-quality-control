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


def test_qc_rules_estimates_ct_and_flags_late_amplification():
    inferred = [
        {
            "run_id": "r1",
            "plate_id": "p1",
            "well_id": "B02",
            "sample_id": "s1",
            "target_id": "t1",
            "cycle": 35,
            "state": "baseline_noise",
            "state_confidence": 0.8,
            "f_adj": 0.05,
        },
        {
            "run_id": "r1",
            "plate_id": "p1",
            "well_id": "B02",
            "sample_id": "s1",
            "target_id": "t1",
            "cycle": 36,
            "state": "exponential_amplification",
            "state_confidence": 0.8,
            "f_adj": 0.25,
        },
        {
            "run_id": "r1",
            "plate_id": "p1",
            "well_id": "B02",
            "sample_id": "s1",
            "target_id": "t1",
            "cycle": 37,
            "state": "linear_transition",
            "state_confidence": 0.75,
            "f_adj": 0.45,
        },
    ]
    calls = apply_qc_rules(inferred, plate_meta={})
    flags = json.loads(calls[0]["qc_flags"])
    assert calls[0]["ct_estimate"] is not None
    assert calls[0]["qc_status"] == "review"
    assert "late_amplification" in flags


def test_qc_rules_flags_positive_control_failure():
    inferred = [
        {
            "run_id": "r1",
            "plate_id": "p1",
            "well_id": "A12",
            "sample_id": "pos1",
            "target_id": "t1",
            "cycle": 1,
            "state": "baseline_noise",
            "state_confidence": 0.95,
            "f_adj": 0.01,
        },
        {
            "run_id": "r1",
            "plate_id": "p1",
            "well_id": "A12",
            "sample_id": "pos1",
            "target_id": "t1",
            "cycle": 2,
            "state": "baseline_noise",
            "state_confidence": 0.95,
            "f_adj": 0.02,
        },
    ]
    meta = {("p1", "A12"): {"control_type": "positive_control"}}
    calls = apply_qc_rules(inferred, plate_meta=meta)
    flags = json.loads(calls[0]["qc_flags"])
    assert calls[0]["qc_status"] == "rerun"
    assert "positive_control_failure" in flags
