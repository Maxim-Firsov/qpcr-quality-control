"""CLI entrypoint for qPCR quality control pipeline."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from datetime import datetime, UTC
from pathlib import Path

from src.core.aggregate import summarize_plates
from src.core.features import build_features
from src.core.hmm_infer import infer_state_paths, load_model_config
from src.core.normalize import normalize_rows
from src.core.qc_rules import apply_qc_rules
from src.core.validate import validate_rows
from src.export.writers import write_csv, write_json
from src.io.csv_loader import load_curve_csv, load_plate_meta_csv
from src.io.rdml_loader import load_rdml
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
    parser = argparse.ArgumentParser(description="Run qPCR quality control pipeline.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--curve-csv", required=False, help="Canonical curve CSV input path.")
    mode.add_argument("--rdml", required=False, help="RDML file or directory path.")
    parser.add_argument("--plate-meta-csv", required=False, help="Optional plate metadata CSV path.")
    parser.add_argument("--outdir", required=True, help="Output directory.")
    parser.add_argument("--min-cycles", type=int, default=3, help="Minimum cycles per well-target.")
    return parser.parse_args(argv)


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _hash_input_path(path_text: str) -> str:
    if not path_text:
        return ""
    path = Path(path_text)
    if not path.exists():
        return ""
    if path.is_file():
        return _hash_file(path)
    if path.is_dir():
        digest = hashlib.sha256()
        for child in sorted(path.rglob("*")):
            if not child.is_file():
                continue
            rel = child.relative_to(path).as_posix().encode("utf-8")
            digest.update(rel)
            digest.update(_hash_file(child).encode("utf-8"))
        return digest.hexdigest()
    return ""


def run_pipeline(args: argparse.Namespace) -> dict:
    started = time.perf_counter()
    generated_at_utc = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    rdml_arg = getattr(args, "rdml", None)
    curve_csv_arg = getattr(args, "curve_csv", None)
    if rdml_arg:
        # RDML mode can process a single file or an entire directory in one run.
        rdml_path = Path(rdml_arg)
        rdml_files = sorted(rdml_path.glob("*.rdml")) if rdml_path.is_dir() else [rdml_path]
        raw: list[dict] = []
        for rdml_file in rdml_files:
            raw.extend(load_rdml(rdml_file))
        execution_mode = "rdml"
    else:
        raw = load_curve_csv(curve_csv_arg)
        execution_mode = "curve_csv"

    normalized = normalize_rows(raw)
    eligible, rejected, validation_summary = validate_rows(normalized, min_cycles=args.min_cycles)
    features = build_features(eligible)
    model_config = load_model_config()
    inferred = infer_state_paths(features, model_config_path=model_config["path"])
    plate_meta = load_plate_meta_csv(args.plate_meta_csv) if args.plate_meta_csv else {}
    well_calls = apply_qc_rules(inferred, plate_meta=plate_meta)
    plate_summary = summarize_plates(well_calls, generated_at_utc=generated_at_utc)

    rerun_manifest = []
    for row in well_calls:
        if row["qc_status"] != "rerun":
            continue
        # Rerun manifest keeps a compact reason string for downstream triage and audit records.
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

    elapsed_seconds = round(time.perf_counter() - started, 6)
    warnings = []
    if rejected:
        warnings.append(f"rejected_rows_present:{len(rejected)}")

    metadata = {
        "schema_version": "v0.1.0",
        "tool_version": "0.1.0",
        "execution_mode": execution_mode,
        "inputs": {
            "curve_csv": str(curve_csv_arg or ""),
            "rdml": str(rdml_arg or ""),
            "plate_meta_csv": str(args.plate_meta_csv or ""),
        },
        "input_hashes": {
            "curve_csv_sha256": _hash_input_path(str(curve_csv_arg or "")),
            "rdml_sha256": _hash_input_path(str(rdml_arg or "")),
            "plate_meta_csv_sha256": _hash_input_path(str(args.plate_meta_csv or "")),
        },
        "input_snapshot_date": generated_at_utc[:10],
        "record_counts": {
            "raw_rows": len(raw),
            "normalized_rows": len(normalized),
            "eligible_rows": len(eligible),
            "rejected_rows": len(rejected),
        },
        "model_config": {"name": "model_v1", "hash": model_config["sha256"]},
        # Validation summary is preserved in metadata so rejected-row reasons remain traceable.
        "data_validation_summary": validation_summary,
        "timing_seconds": elapsed_seconds,
        "warnings": warnings,
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
