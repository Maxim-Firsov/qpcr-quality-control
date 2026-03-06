"""CLI entrypoint for qPCR HMM QC scaffold."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.core.aggregate import summarize_plates
from src.core.features import build_features
from src.core.hmm_infer import infer_state_paths
from src.core.normalize import normalize_rows
from src.core.qc_rules import apply_qc_rules
from src.core.validate import validate_rows
from src.export.writers import write_csv, write_json
from src.io.csv_loader import load_curve_csv, load_plate_meta_csv
from src.report.render import render_report

WELL_CALL_FIELDS = [
    "run_id",
    "plate_id",
    "well_id",
    "sample_id",
    "target_id",
    "control_type",
    "ct_estimate",
    "hmm_state_path_compact",
    "amplification_confidence",
    "call_label",
    "qc_status",
    "qc_flags",
]

RERUN_FIELDS = [
    "plate_id",
    "well_id",
    "target_id",
    "sample_id",
    "rerun_reason",
    "evidence_score",
    "recommended_action",
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run qPCR HMM QC pipeline in canonical CSV mode.")
    parser.add_argument("--curve-csv", required=True, help="Canonical curve CSV input path.")
    parser.add_argument("--plate-meta-csv", required=False, help="Optional plate metadata CSV path.")
    parser.add_argument("--outdir", required=True, help="Output directory.")
    parser.add_argument("--min-cycles", type=int, default=3, help="Minimum cycles per well-target.")
    return parser.parse_args(argv)


def run_pipeline(args: argparse.Namespace) -> dict:
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    raw = load_curve_csv(args.curve_csv)
    normalized = normalize_rows(raw)
    eligible, rejected, validation_summary = validate_rows(normalized, min_cycles=args.min_cycles)
    features = build_features(eligible)
    inferred = infer_state_paths(features)
    plate_meta = load_plate_meta_csv(args.plate_meta_csv) if args.plate_meta_csv else {}
    well_calls = apply_qc_rules(inferred, plate_meta=plate_meta)
    plate_summary = summarize_plates(well_calls)

    rerun_manifest = []
    for row in well_calls:
        if row["qc_status"] != "rerun":
            continue
        flags = json.loads(row["qc_flags"])
        rerun_manifest.append(
            {
                "plate_id": row["plate_id"],
                "well_id": row["well_id"],
                "target_id": row["target_id"],
                "sample_id": row["sample_id"],
                "rerun_reason": ",".join(flags) if flags else "manual_review",
                "evidence_score": row["amplification_confidence"],
                "recommended_action": "repeat_well_qpcr",
            }
        )

    metadata = {
        "schema_version": "v0.1.0",
        "tool_version": "0.1.0",
        "execution_mode": "curve_csv",
        "inputs": {"curve_csv": str(args.curve_csv), "plate_meta_csv": str(args.plate_meta_csv or "")},
        "input_snapshot_date": "1970-01-01",
        "record_counts": {
            "raw_rows": len(raw),
            "normalized_rows": len(normalized),
            "eligible_rows": len(eligible),
            "rejected_rows": len(rejected),
        },
        "model_config": {"name": "model_v1", "hash": "deterministic-scaffold"},
        "data_validation_summary": validation_summary,
        "timing_seconds": 0.0,
        "warnings": [],
    }

    write_csv(outdir / "well_calls.csv", well_calls, WELL_CALL_FIELDS)
    write_csv(outdir / "rerun_manifest.csv", rerun_manifest, RERUN_FIELDS)
    write_json(outdir / "plate_qc_summary.json", plate_summary)
    write_json(outdir / "run_metadata.json", metadata)
    (outdir / "report.html").write_text(render_report(plate_summary), encoding="utf-8")

    return {
        "well_calls": len(well_calls),
        "rerun_manifest": len(rerun_manifest),
        "plate_count": len(plate_summary["plates"]),
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    run_pipeline(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
