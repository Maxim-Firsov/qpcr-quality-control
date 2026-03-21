"""Execute one workflow manifest row while preserving batch-level aggregation artifacts on failure."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from src.cli import run_pipeline
from src.export.writers import write_json


def _timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_manifest(path: str | Path) -> dict:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _write_failure_outputs(run_record: dict, message: str) -> None:
    run_dir = Path(run_record["run_dir"])
    run_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "schema_version": "v0.1.0",
        "generated_at_utc": _timestamp(),
        "run_id": run_record["run_id"],
        "execution_status": "failed",
        "execution_mode": run_record["input_mode"],
        "plate_schema": run_record["plate_schema"],
        "artifact_profile": run_record["artifact_profile"],
        "run_status": "unavailable",
        "plate_count": 0,
        "pass_count": 0,
        "review_count": 0,
        "rerun_count": 0,
        "rerun_well_count": 0,
        "warning_count": 1,
        "warnings": [{"code": "workflow_execution_failed", "message": message, "severity": "error"}],
        "status_reason_counts": [],
        "counts": {
            "well_calls": 0,
            "well_calls_written": 0,
            "rerun_manifest": 0,
            "plate_count": 0,
            "raw_rows": 0,
            "eligible_rows": 0,
            "rejected_rows": 0,
        },
        "global_counts": {"pass": 0, "review": 0, "rerun": 0},
        "timing_seconds": 0.0,
        "peak_memory_mb": 0.0,
        "warning_codes": ["workflow_execution_failed"],
        "artifact_inventory": {
            "summary.json": {"generated": True, "path": str(run_dir / "summary.json"), "reason": "failure_placeholder"},
            "run_metadata.json": {"generated": True, "path": str(run_dir / "run_metadata.json"), "reason": "failure_placeholder"},
            "plate_qc_summary.json": {"generated": False, "path": str(run_dir / "plate_qc_summary.json"), "reason": "analysis_failed"},
            "rerun_manifest.csv": {"generated": False, "path": str(run_dir / "rerun_manifest.csv"), "reason": "analysis_failed"},
            "well_calls.csv": {"generated": False, "path": str(run_dir / "well_calls.csv"), "reason": "analysis_failed"},
            "report.html": {"generated": False, "path": str(run_dir / "report.html"), "reason": "analysis_failed"},
        },
    }
    metadata = {
        "schema_version": "v0.1.0",
        "tool_version": "0.1.0",
        "run_id": run_record["run_id"],
        "execution_mode": run_record["input_mode"],
        "plate_schema": run_record["plate_schema"],
        "artifact_profile": run_record["artifact_profile"],
        "inputs": {
            "curve_csv": run_record["input_path"] if run_record["input_mode"] == "curve_csv" else "",
            "rdml": run_record["input_path"] if run_record["input_mode"] == "rdml" else "",
            "plate_meta_csv": run_record["plate_meta_csv"],
            "control_map_config": run_record["control_map_config"],
        },
        "warnings": summary["warnings"],
        "warning_codes": summary["warning_codes"],
        "artifact_inventory": summary["artifact_inventory"],
        "data_validation_summary": {},
        "record_counts": {"raw_rows": 0, "normalized_rows": 0, "eligible_rows": 0, "rejected_rows": 0},
        "model_config": {},
        "normalization": {"requested_profile": run_record["normalization_profile"], "config_path": run_record["normalization_config"], "config_sha256": ""},
        "control_map": {"config_path": run_record["control_map_config"], "config_sha256": ""},
        "melt_qc": {"well_target_count": 0, "review_count": 0},
        "input_hashes": {},
        "input_snapshot_date": summary["generated_at_utc"][:10],
        "timing_seconds": 0.0,
        "stage_timings_seconds": {},
        "peak_memory_mb": 0.0,
        "qc_thresholds": {
            "confidence_threshold": run_record["confidence_threshold"],
            "late_ct_threshold": run_record["late_ct_threshold"],
            "low_signal_threshold": run_record["low_signal_threshold"],
            "replicate_ct_spread_threshold": run_record["replicate_ct_spread_threshold"],
            "replicate_ct_outlier_threshold": run_record["replicate_ct_outlier_threshold"],
        },
    }
    write_json(run_dir / "summary.json", summary)
    write_json(run_dir / "run_metadata.json", metadata)


def execute_run(validated_manifest_path: str | Path, run_id: str) -> dict:
    payload = _load_manifest(validated_manifest_path)
    records = {row["run_id"]: row for row in payload["rows"]}
    if run_id not in records:
        raise ValueError(f"Run id {run_id!r} is not present in {validated_manifest_path}.")
    run_record = records[run_id]
    run_dir = Path(run_record["run_dir"])
    run_dir.mkdir(parents=True, exist_ok=True)
    started_at = _timestamp()
    status_path = run_dir / "workflow_status.json"
    try:
        result = run_pipeline(
            argparse.Namespace(
                run_id=run_record["run_id"],
                rdml=run_record["input_path"] if run_record["input_mode"] == "rdml" else None,
                curve_csv=run_record["input_path"] if run_record["input_mode"] == "curve_csv" else None,
                plate_meta_csv=run_record["plate_meta_csv"] or None,
                control_map_config=run_record["control_map_config"] or None,
                outdir=str(run_dir),
                min_cycles=run_record["min_cycles"],
                allow_empty_run=run_record["allow_empty_run"],
                plate_schema=run_record["plate_schema"],
                confidence_threshold=run_record["confidence_threshold"],
                late_ct_threshold=run_record["late_ct_threshold"],
                low_signal_threshold=run_record["low_signal_threshold"],
                replicate_ct_spread_threshold=run_record["replicate_ct_spread_threshold"],
                replicate_ct_outlier_threshold=run_record["replicate_ct_outlier_threshold"],
                normalization_profile=run_record["normalization_profile"],
                normalization_config=run_record["normalization_config"] or None,
                artifact_profile=run_record["artifact_profile"],
            )
        )
        workflow_status = {
            "run_id": run_record["run_id"],
            "execution_status": "succeeded",
            "started_at_utc": started_at,
            "finished_at_utc": _timestamp(),
            "summary_path": str(run_dir / "summary.json"),
            "run_dir": str(run_dir),
        }
        write_json(status_path, workflow_status)
        return result
    except Exception as exc:
        _write_failure_outputs(run_record, str(exc))
        workflow_status = {
            "run_id": run_record["run_id"],
            "execution_status": "failed",
            "started_at_utc": started_at,
            "finished_at_utc": _timestamp(),
            "summary_path": str(run_dir / "summary.json"),
            "run_dir": str(run_dir),
            "error_message": str(exc),
        }
        write_json(status_path, workflow_status)
        return workflow_status


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Execute one run from a validated qPCR batch manifest.")
    parser.add_argument("--validated-manifest", required=True)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args(argv)
    execute_run(args.validated_manifest, args.run_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
