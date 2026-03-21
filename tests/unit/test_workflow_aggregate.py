import json

from src.export.writers import write_csv, write_json
from src.workflow.aggregate_batch import aggregate_batch


def test_aggregate_batch_builds_gate_outputs(tmp_path):
    batch_root = tmp_path / "batch_out"
    run_a = batch_root / "runs" / "run_a"
    run_b = batch_root / "runs" / "run_b"
    run_a.mkdir(parents=True)
    run_b.mkdir(parents=True)

    validated_manifest = {
        "schema_version": "v0.1.0",
        "manifest_path": str(tmp_path / "manifest.tsv"),
        "manifest_sha256": "abc123",
        "artifact_profile": "review",
        "batch_id": "batch_out",
        "output_root": str(batch_root),
        "run_count": 2,
        "rows": [
            {"run_id": "run_a", "run_dir": str(run_a)},
            {"run_id": "run_b", "run_dir": str(run_b)},
        ],
    }
    write_json(tmp_path / "validated_manifest.json", validated_manifest)
    write_json(
        run_a / "summary.json",
        {
            "run_id": "run_a",
            "run_status": "pass",
            "execution_status": "succeeded",
            "plate_count": 1,
            "pass_count": 1,
            "review_count": 0,
            "rerun_count": 0,
            "rerun_well_count": 0,
            "warning_count": 0,
            "artifact_inventory": {},
            "status_reason_counts": [],
        },
    )
    write_json(run_a / "workflow_status.json", {"run_id": "run_a", "execution_status": "succeeded"})
    write_csv(
        run_a / "rerun_manifest.csv",
        [],
        ["plate_id", "well_id", "target_id", "sample_id", "rerun_reason", "evidence_score", "recommended_action"],
    )
    write_json(
        run_b / "summary.json",
        {
            "run_id": "run_b",
            "run_status": "rerun",
            "execution_status": "succeeded",
            "plate_count": 1,
            "pass_count": 0,
            "review_count": 1,
            "rerun_count": 1,
            "rerun_well_count": 1,
            "warning_count": 1,
            "artifact_inventory": {},
            "status_reason_counts": [{"reason": "ntc_contamination", "review_count": 0, "rerun_count": 1, "well_count": 1}],
        },
    )
    write_json(run_b / "workflow_status.json", {"run_id": "run_b", "execution_status": "succeeded"})
    write_csv(
        run_b / "rerun_manifest.csv",
        [
            {
                "plate_id": "p1",
                "well_id": "A01",
                "target_id": "t1",
                "sample_id": "s1",
                "rerun_reason": "ntc_contamination",
                "evidence_score": "0.95",
                "recommended_action": "repeat_well_qpcr",
            }
        ],
        ["plate_id", "well_id", "target_id", "sample_id", "rerun_reason", "evidence_score", "recommended_action"],
    )

    policy = tmp_path / "policy.yaml"
    policy.write_text(
        json.dumps(
            {
                "max_failed_runs_for_release": 0,
                "max_rerun_wells_for_release": 0,
                "max_review_wells_for_release": 0,
                "max_review_runs_for_release": 0,
            }
        ),
        encoding="utf-8",
    )

    aggregated = aggregate_batch(tmp_path / "validated_manifest.json", config_path=policy)

    assert aggregated["batch_master"]["release_status"] == "block"
    assert aggregated["batch_gate_status"]["blocking_reasons"] == ["rerun_wells_present"]
    assert aggregated["rerun_queue"][0]["run_id"] == "run_b"
    assert aggregated["failure_reason_counts"][0]["failure_reason"] == "ntc_contamination"
