"""CLI entrypoint for qPCR quality control pipeline."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import time
import tracemalloc
from datetime import datetime, UTC
from pathlib import Path

from src.core.aggregate import summarize_plates
from src.core.control_map import build_plate_meta, load_control_map
from src.core.features import build_features
from src.core.hmm_infer import infer_state_paths, load_model_config
from src.core.melt_qc import analyze_melt_curves
from src.core.normalization_profiles import load_normalization_profiles
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


def _warning(code: str, message: str, severity: str = "warning") -> dict:
    return {"code": code, "message": message, "severity": severity}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run qPCR quality control pipeline.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--curve-csv", required=False, help="Canonical curve CSV input path.")
    mode.add_argument("--rdml", required=False, help="RDML file or directory path.")
    mode.add_argument("--batch-manifest", required=False, help="CSV manifest describing multiple pipeline runs.")
    parser.add_argument("--plate-meta-csv", required=False, help="Optional plate metadata CSV path.")
    parser.add_argument("--control-map-config", required=False, help="Optional JSON control-map config for assay-specific layouts.")
    parser.add_argument("--outdir", required=True, help="Output directory.")
    parser.add_argument("--min-cycles", type=int, default=3, help="Minimum cycles per well-target.")
    parser.add_argument("--confidence-threshold", type=float, default=0.6, help="Minimum mean state confidence before a call is downgraded to review.")
    parser.add_argument("--late-ct-threshold", type=float, default=35.0, help="Ct threshold at or above which amplification is marked late.")
    parser.add_argument("--low-signal-threshold", type=float, default=0.15, help="Adjusted fluorescence ceiling below which a trace is marked low signal.")
    parser.add_argument("--replicate-ct-spread-threshold", type=float, default=2.0, help="Ct spread above which replicate groups are marked review.")
    parser.add_argument("--replicate-ct-outlier-threshold", type=float, default=1.5, help="Ct distance from replicate-group median above which an amplified replicate is marked as an outlier.")
    parser.add_argument(
        "--plate-schema",
        choices=["auto", "96", "384"],
        default="auto",
        help="Plate geometry used for edge-aware QC logic. Default: auto.",
    )
    parser.add_argument(
        "--allow-empty-run",
        action="store_true",
        help="Write empty outputs instead of failing when all rows are rejected during validation.",
    )
    parser.add_argument(
        "--normalization-profile",
        default="auto",
        help="Normalization profile name from config, or 'auto' to resolve by instrument/assay.",
    )
    parser.add_argument(
        "--normalization-config",
        required=False,
        help="Optional JSON config path for normalization profiles.",
    )
    parser.add_argument("--fail-on-review", action="store_true", help="Exit non-zero if any well-target is marked review.")
    parser.add_argument("--fail-on-rerun", action="store_true", help="Exit non-zero if any well-target is marked rerun.")
    parser.add_argument("--fail-on-edge-alert", action="store_true", help="Exit non-zero if any plate triggers edge_effect_alert.")
    return parser.parse_args(argv)


def _emit_success_summary(result: dict) -> None:
    """Print a concise success summary with the primary output artifact."""
    global_counts = result.get("global_counts", {})
    print(
        (
            "qpcr-quality-control completed: "
            f"{result.get('well_calls', 0)} well call(s), "
            f"{result.get('rerun_manifest', 0)} rerun row(s), "
            f"{result.get('plate_count', 0)} plate(s), "
            f"pass={int(global_counts.get('pass', 0))}, "
            f"review={int(global_counts.get('review', 0))}, "
            f"rerun={int(global_counts.get('rerun', 0))}."
        )
    )
    print(f"Summary: {result.get('summary_path', '')}")


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
    tracemalloc.start()
    started = time.perf_counter()
    generated_at_utc = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    stage_timings: dict[str, float] = {}
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    rdml_arg = getattr(args, "rdml", None)
    curve_csv_arg = getattr(args, "curve_csv", None)
    stage_started = time.perf_counter()
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
    stage_timings["ingest_seconds"] = round(time.perf_counter() - stage_started, 6)

    stage_started = time.perf_counter()
    normalized = normalize_rows(raw)
    melt_summary = analyze_melt_curves(normalized)
    stage_timings["normalize_seconds"] = round(time.perf_counter() - stage_started, 6)

    stage_started = time.perf_counter()
    eligible, rejected, validation_summary = validate_rows(normalized, min_cycles=args.min_cycles)
    stage_timings["validate_seconds"] = round(time.perf_counter() - stage_started, 6)
    allow_empty_run = bool(getattr(args, "allow_empty_run", False))
    if not eligible and not allow_empty_run:
        raise ValueError(
            "No eligible well-target curves remained after validation. "
            "Use --allow-empty-run to emit empty outputs for fully rejected inputs."
        )
    stage_started = time.perf_counter()
    normalization_profiles = load_normalization_profiles(getattr(args, "normalization_config", None))
    requested_profile = getattr(args, "normalization_profile", "auto")
    features = build_features(
        eligible,
        normalization_profiles=normalization_profiles,
        requested_profile=None if requested_profile == "auto" else requested_profile,
    )
    model_config = load_model_config()
    inferred = infer_state_paths(features, model_config_path=model_config["path"])
    stage_timings["infer_seconds"] = round(time.perf_counter() - stage_started, 6)

    stage_started = time.perf_counter()
    plate_meta = load_plate_meta_csv(args.plate_meta_csv) if args.plate_meta_csv else {}
    control_map = load_control_map(args.control_map_config) if getattr(args, "control_map_config", None) else None
    plate_meta = build_plate_meta(plate_meta, inferred_rows=inferred, control_map=control_map)
    well_calls = apply_qc_rules(
        inferred,
        plate_meta=plate_meta,
        melt_summary=melt_summary,
        confidence_threshold=float(getattr(args, "confidence_threshold", 0.6)),
        late_ct_threshold=float(getattr(args, "late_ct_threshold", 35.0)),
        low_signal_threshold=float(getattr(args, "low_signal_threshold", 0.15)),
        plate_schema=args.plate_schema,
        replicate_ct_spread_threshold=float(getattr(args, "replicate_ct_spread_threshold", 2.0)),
        replicate_ct_outlier_threshold=float(getattr(args, "replicate_ct_outlier_threshold", 1.5)),
    )
    plate_summary = summarize_plates(well_calls, generated_at_utc=generated_at_utc, plate_schema=args.plate_schema)
    stage_timings["qc_seconds"] = round(time.perf_counter() - stage_started, 6)

    stage_started = time.perf_counter()
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

    current_bytes, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    elapsed_seconds = round(time.perf_counter() - started, 6)
    peak_memory_mb = round(peak_bytes / (1024 * 1024), 6)
    warnings = []
    if rejected:
        warnings.append(_warning("rejected_rows_present", f"{len(rejected)} rows were rejected during validation."))
    if plate_summary["global_counts"]["review"] > 0:
        warnings.append(
            _warning(
                "review_wells_present",
                f"{plate_summary['global_counts']['review']} well-target calls require review.",
            )
        )
    if plate_summary["global_counts"]["rerun"] > 0:
        warnings.append(
            _warning(
                "rerun_wells_present",
                f"{plate_summary['global_counts']['rerun']} well-target calls were escalated to rerun.",
            )
        )
    stage_timings["postprocess_seconds"] = round(time.perf_counter() - stage_started, 6)

    metadata = {
        "schema_version": "v0.1.0",
        "tool_version": "0.1.0",
        "execution_mode": execution_mode,
        "plate_schema": args.plate_schema,
        "qc_thresholds": {
            "confidence_threshold": float(getattr(args, "confidence_threshold", 0.6)),
            "late_ct_threshold": float(getattr(args, "late_ct_threshold", 35.0)),
            "low_signal_threshold": float(getattr(args, "low_signal_threshold", 0.15)),
            "replicate_ct_spread_threshold": float(getattr(args, "replicate_ct_spread_threshold", 2.0)),
            "replicate_ct_outlier_threshold": float(getattr(args, "replicate_ct_outlier_threshold", 1.5)),
        },
        "inputs": {
            "curve_csv": str(curve_csv_arg or ""),
            "rdml": str(rdml_arg or ""),
            "plate_meta_csv": str(args.plate_meta_csv or ""),
            "control_map_config": str(getattr(args, "control_map_config", "") or ""),
        },
        "input_hashes": {
            "curve_csv_sha256": _hash_input_path(str(curve_csv_arg or "")),
            "rdml_sha256": _hash_input_path(str(rdml_arg or "")),
            "plate_meta_csv_sha256": _hash_input_path(str(args.plate_meta_csv or "")),
            "control_map_config_sha256": _hash_input_path(str(getattr(args, "control_map_config", "") or "")),
        },
        "input_snapshot_date": generated_at_utc[:10],
        "record_counts": {
            "raw_rows": len(raw),
            "normalized_rows": len(normalized),
            "eligible_rows": len(eligible),
            "rejected_rows": len(rejected),
        },
        "model_config": {"name": "model_v1", "hash": model_config["sha256"]},
        "normalization": {
            "requested_profile": requested_profile,
            "config_path": normalization_profiles["_path"],
            "config_sha256": normalization_profiles["_sha256"],
        },
        "control_map": {
            "config_path": control_map["_path"] if control_map else "",
            "config_sha256": control_map["_sha256"] if control_map else "",
        },
        "melt_qc": {
            "well_target_count": len(melt_summary),
            "review_count": sum(1 for item in melt_summary.values() if item.get("status") == "review"),
        },
        # Validation summary is preserved in metadata so rejected-row reasons remain traceable.
        "data_validation_summary": validation_summary,
        "timing_seconds": elapsed_seconds,
        "stage_timings_seconds": stage_timings,
        "peak_memory_mb": peak_memory_mb,
        "warnings": warnings,
        "warning_codes": [warning["code"] for warning in warnings],
    }

    stage_started = time.perf_counter()
    write_csv(outdir / "well_calls.csv", well_calls, WELL_CALL_FIELDS)
    write_csv(outdir / "rerun_manifest.csv", rerun_manifest, RERUN_FIELDS)
    write_json(outdir / "plate_qc_summary.json", plate_summary)
    write_json(outdir / "run_metadata.json", metadata)
    summary_payload = {
        "schema_version": "v0.1.0",
        "generated_at_utc": generated_at_utc,
        "execution_mode": execution_mode,
        "plate_schema": args.plate_schema,
        "counts": {
            "well_calls": len(well_calls),
            "rerun_manifest": len(rerun_manifest),
            "plate_count": len(plate_summary["plates"]),
            "raw_rows": len(raw),
            "eligible_rows": len(eligible),
            "rejected_rows": len(rejected),
        },
        "global_counts": plate_summary["global_counts"],
        "timing_seconds": elapsed_seconds,
        "peak_memory_mb": peak_memory_mb,
        "warning_codes": metadata["warning_codes"],
    }
    write_json(outdir / "summary.json", summary_payload)
    (outdir / "report.html").write_text(render_report(plate_summary, well_calls=well_calls, curve_rows=inferred), encoding="utf-8")
    stage_timings["export_seconds"] = round(time.perf_counter() - stage_started, 6)
    metadata["stage_timings_seconds"] = stage_timings
    write_json(outdir / "run_metadata.json", metadata)

    return {
        "well_calls": len(well_calls),
        "rerun_manifest": len(rerun_manifest),
        "plate_count": len(plate_summary["plates"]),
        "global_counts": plate_summary["global_counts"],
        "edge_alert_plates": [plate["plate_id"] for plate in plate_summary["plates"] if plate.get("edge_effect_alert")],
        "summary_path": str(outdir / "summary.json"),
    }


def _policy_failures(result: dict, fail_on_review: bool, fail_on_rerun: bool, fail_on_edge_alert: bool) -> list[str]:
    failures: list[str] = []
    global_counts = result.get("global_counts", {})
    if fail_on_review and int(global_counts.get("review", 0)) > 0:
        failures.append(f"review_wells_present:{global_counts['review']}")
    if fail_on_rerun and int(global_counts.get("rerun", 0)) > 0:
        failures.append(f"rerun_wells_present:{global_counts['rerun']}")
    edge_alert_plates = result.get("edge_alert_plates", [])
    if fail_on_edge_alert and edge_alert_plates:
        failures.append(f"edge_alert_plates:{','.join(edge_alert_plates)}")
    return failures


def _manifest_rows(path: str | Path) -> list[dict]:
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def run_batch_manifest(args: argparse.Namespace) -> dict:
    manifest_path = Path(args.batch_manifest)
    rows = _manifest_rows(manifest_path)
    results = []
    for index, row in enumerate(rows, start=1):
        input_mode = (row.get("input_mode") or "").strip().lower()
        if input_mode not in {"rdml", "curve_csv"}:
            raise ValueError(f"Unsupported input_mode in batch manifest row {index}: {input_mode!r}")
        run_args = argparse.Namespace(
            rdml=row.get("input_path") if input_mode == "rdml" else None,
            curve_csv=row.get("input_path") if input_mode == "curve_csv" else None,
            plate_meta_csv=row.get("plate_meta_csv") or None,
            control_map_config=row.get("control_map_config") or args.control_map_config,
            outdir=row.get("outdir") or str(Path(args.outdir) / f"batch_run_{index:03d}"),
            min_cycles=int(row.get("min_cycles") or args.min_cycles),
            allow_empty_run=str(row.get("allow_empty_run") or "").strip().lower() in {"1", "true", "yes"},
            plate_schema=(row.get("plate_schema") or args.plate_schema or "auto"),
            confidence_threshold=float(row.get("confidence_threshold") or args.confidence_threshold),
            late_ct_threshold=float(row.get("late_ct_threshold") or args.late_ct_threshold),
            low_signal_threshold=float(row.get("low_signal_threshold") or args.low_signal_threshold),
            replicate_ct_spread_threshold=float(row.get("replicate_ct_spread_threshold") or args.replicate_ct_spread_threshold),
            replicate_ct_outlier_threshold=float(row.get("replicate_ct_outlier_threshold") or args.replicate_ct_outlier_threshold),
            normalization_profile=row.get("normalization_profile") or args.normalization_profile,
            normalization_config=row.get("normalization_config") or args.normalization_config,
        )
        result = run_pipeline(run_args)
        result["manifest_row"] = index
        result["input_mode"] = input_mode
        result["input_path"] = row.get("input_path", "")
        results.append(result)

    batch_summary = {
        "schema_version": "v0.1.0",
        "manifest_path": str(manifest_path),
        "run_count": len(results),
        "results": results,
    }
    write_json(Path(args.outdir) / "batch_summary.json", batch_summary)
    return batch_summary


def main(argv: list[str] | None = None) -> int:
    try:
        args = parse_args(argv)
        if getattr(args, "batch_manifest", None):
            batch_summary = run_batch_manifest(args)
            failures = []
            for result in batch_summary["results"]:
                _emit_success_summary(result)
                failures.extend(
                    _policy_failures(
                        result,
                        fail_on_review=args.fail_on_review,
                        fail_on_rerun=args.fail_on_rerun,
                        fail_on_edge_alert=args.fail_on_edge_alert,
                    )
                )
        else:
            result = run_pipeline(args)
            _emit_success_summary(result)
            failures = _policy_failures(
                result,
                fail_on_review=args.fail_on_review,
                fail_on_rerun=args.fail_on_rerun,
                fail_on_edge_alert=args.fail_on_edge_alert,
            )
        if failures:
            print("qpcr-quality-control policy failure: " + "; ".join(failures), file=sys.stderr)
            return 2
        return 0
    except ValueError as exc:
        print(f"qpcr-quality-control: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
