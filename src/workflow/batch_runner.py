"""Execute one workflow manifest row while preserving batch-level aggregation artifacts on failure."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from src.cli import WELL_CALL_FIELDS, run_pipeline
from src.export.writers import write_csv, write_json

RERUN_FIELDS = [
    "plate_id",
    "well_id",
    "target_id",
    "sample_id",
    "rerun_reason",
    "evidence_score",
    "recommended_action",
]


def _timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_manifest(path: str | Path) -> dict:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _load_run_record(path: str | Path) -> dict:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _write_placeholder_well_calls(path: Path) -> None:
    write_csv(path, [], WELL_CALL_FIELDS)


def _write_placeholder_report(path: Path, reason: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        (
            "<html><head><meta charset='utf-8'><title>qPCR QC Report Placeholder</title></head>"
            f"<body><p>{reason}</p></body></html>"
        ),
        encoding="utf-8",
    )


def _mark_placeholder_artifact(inventory: dict, name: str, path: Path, reason: str) -> None:
    inventory[name] = {
        "generated": True,
        "path": str(path),
        "reason": reason,
    }


def _load_json(path: str | Path) -> dict:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _ensure_tracked_optional_artifacts(run_dir: Path, placeholder_reason_prefix: str = "placeholder") -> None:
    summary_path = run_dir / "summary.json"
    metadata_path = run_dir / "run_metadata.json"
    summary = _load_json(summary_path)
    metadata = _load_json(metadata_path)
    inventory = summary.get("artifact_inventory", {})

    well_calls_path = run_dir / "well_calls.csv"
    if not well_calls_path.exists():
        reason = f"{placeholder_reason_prefix}_well_calls"
        _write_placeholder_well_calls(well_calls_path)
        _mark_placeholder_artifact(inventory, "well_calls.csv", well_calls_path, reason)

    report_path = run_dir / "report.html"
    if not report_path.exists():
        reason = f"{placeholder_reason_prefix}_report_html"
        _write_placeholder_report(report_path, "Reviewer-facing report omitted or unavailable for this run.")
        _mark_placeholder_artifact(inventory, "report.html", report_path, reason)

    summary["artifact_inventory"] = inventory
    metadata["artifact_inventory"] = inventory
    write_json(summary_path, summary)
    write_json(metadata_path, metadata)


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
            "plate_qc_summary.json": {"generated": True, "path": str(run_dir / "plate_qc_summary.json"), "reason": "failure_placeholder"},
            "rerun_manifest.csv": {"generated": True, "path": str(run_dir / "rerun_manifest.csv"), "reason": "failure_placeholder"},
            "well_calls.csv": {"generated": True, "path": str(run_dir / "well_calls.csv"), "reason": "failure_placeholder"},
            "report.html": {"generated": True, "path": str(run_dir / "report.html"), "reason": "failure_placeholder"},
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
    _write_placeholder_well_calls(run_dir / "well_calls.csv")
    _write_placeholder_report(run_dir / "report.html", "Run failed before reviewer-facing artifacts could be rendered.")
    plate_qc_summary = {
        "schema_version": "v0.1.0",
        "generated_at_utc": summary["generated_at_utc"],
        "plates": [],
        "global_counts": {"pass": 0, "review": 0, "rerun": 0},
    }
    write_csv(run_dir / "rerun_manifest.csv", [], RERUN_FIELDS)
    write_json(run_dir / "plate_qc_summary.json", plate_qc_summary)
    write_json(run_dir / "summary.json", summary)
    write_json(run_dir / "run_metadata.json", metadata)


def execute_run(validated_manifest_path: str | Path, run_id: str) -> dict:
    payload = _load_manifest(validated_manifest_path)
    if payload.get("validation_status") != "valid":
        raise ValueError("Validated manifest must have validation_status='valid' before run execution.")
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
        _ensure_tracked_optional_artifacts(run_dir, placeholder_reason_prefix="workflow_tracked")
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


def execute_run_record(run_record_path: str | Path) -> dict:
    run_record = _load_run_record(run_record_path)
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
        _ensure_tracked_optional_artifacts(run_dir, placeholder_reason_prefix="workflow_tracked")
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
    parser.add_argument("--validated-manifest", required=False)
    parser.add_argument("--run-id", required=False)
    parser.add_argument("--run-record", required=False)
    args = parser.parse_args(argv)
    if args.run_record:
        execute_run_record(args.run_record)
    elif args.validated_manifest and args.run_id:
        execute_run(args.validated_manifest, args.run_id)
    else:
        raise ValueError("Provide either --run-record or both --validated-manifest and --run-id.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
