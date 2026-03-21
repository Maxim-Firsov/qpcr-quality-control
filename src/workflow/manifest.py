"""Manifest validation and normalization for workflow-mode batch execution."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from pathlib import Path

from src.cli import ARTIFACT_PROFILES
from src.export.writers import write_json

RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")
REQUIRED_COLUMNS = ("run_id", "input_mode", "input_path")
OPTIONAL_COLUMNS = (
    "plate_meta_csv",
    "control_map_config",
    "min_cycles",
    "plate_schema",
    "allow_empty_run",
    "confidence_threshold",
    "late_ct_threshold",
    "low_signal_threshold",
    "replicate_ct_spread_threshold",
    "replicate_ct_outlier_threshold",
    "normalization_profile",
    "normalization_config",
)


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_manifest_rows(manifest_path: Path) -> list[dict]:
    with manifest_path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def _resolve_optional_path(manifest_dir: Path, value: str | None) -> str:
    if not value:
        return ""
    path = Path(value)
    if not path.is_absolute():
        manifest_relative = manifest_dir / path
        if manifest_relative.exists():
            path = manifest_relative
        else:
            path = Path.cwd() / path
    return str(path.resolve())


def validate_manifest(
    manifest_path: str | Path,
    output_root: str | Path,
    artifact_profile: str = "review",
) -> dict:
    manifest_path = Path(manifest_path).resolve()
    if artifact_profile not in ARTIFACT_PROFILES:
        raise ValueError(f"Unsupported artifact profile: {artifact_profile!r}")
    rows = _read_manifest_rows(manifest_path)
    if not rows:
        raise ValueError("Batch manifest is empty.")
    header = tuple(rows[0].keys())
    missing = [column for column in REQUIRED_COLUMNS if column not in header]
    if missing:
        raise ValueError(f"Batch manifest is missing required columns: {', '.join(missing)}")

    manifest_dir = manifest_path.parent
    output_root = Path(output_root).resolve()
    normalized_rows = []
    seen_run_ids: set[str] = set()
    for index, row in enumerate(rows, start=1):
        run_id = str(row.get("run_id") or "").strip()
        if not run_id:
            raise ValueError(f"Manifest row {index} is missing run_id.")
        if not RUN_ID_PATTERN.match(run_id):
            raise ValueError(f"Manifest row {index} has invalid run_id {run_id!r}. Use letters, numbers, '.', '_', or '-'.")
        if run_id in seen_run_ids:
            raise ValueError(f"Manifest row {index} reuses run_id {run_id!r}.")
        seen_run_ids.add(run_id)

        input_mode = str(row.get("input_mode") or "").strip().lower()
        if input_mode not in {"rdml", "curve_csv"}:
            raise ValueError(f"Manifest row {index} has unsupported input_mode {input_mode!r}.")
        input_path = Path(_resolve_optional_path(manifest_dir, row.get("input_path")))
        if not input_path.exists():
            raise ValueError(f"Manifest row {index} input_path does not exist: {input_path}")
        if input_mode == "curve_csv" and not input_path.is_file():
            raise ValueError(f"Manifest row {index} curve_csv input_path must be a file: {input_path}")
        if input_mode == "rdml" and not (input_path.is_file() or input_path.is_dir()):
            raise ValueError(f"Manifest row {index} rdml input_path must be a file or directory: {input_path}")

        plate_meta_csv = _resolve_optional_path(manifest_dir, row.get("plate_meta_csv"))
        if plate_meta_csv and not Path(plate_meta_csv).exists():
            raise ValueError(f"Manifest row {index} plate_meta_csv does not exist: {plate_meta_csv}")
        control_map_config = _resolve_optional_path(manifest_dir, row.get("control_map_config"))
        if control_map_config and not Path(control_map_config).exists():
            raise ValueError(f"Manifest row {index} control_map_config does not exist: {control_map_config}")
        normalization_config = _resolve_optional_path(manifest_dir, row.get("normalization_config"))
        if normalization_config and not Path(normalization_config).exists():
            raise ValueError(f"Manifest row {index} normalization_config does not exist: {normalization_config}")

        normalized_rows.append(
            {
                "run_id": run_id,
                "input_mode": input_mode,
                "input_path": str(input_path.resolve()),
                "plate_meta_csv": plate_meta_csv,
                "control_map_config": control_map_config,
                "min_cycles": int(row.get("min_cycles") or 3),
                "plate_schema": str(row.get("plate_schema") or "auto"),
                "allow_empty_run": str(row.get("allow_empty_run") or "").strip().lower() in {"1", "true", "yes"},
                "confidence_threshold": float(row.get("confidence_threshold") or 0.6),
                "late_ct_threshold": float(row.get("late_ct_threshold") or 35.0),
                "low_signal_threshold": float(row.get("low_signal_threshold") or 0.15),
                "replicate_ct_spread_threshold": float(row.get("replicate_ct_spread_threshold") or 2.0),
                "replicate_ct_outlier_threshold": float(row.get("replicate_ct_outlier_threshold") or 1.5),
                "normalization_profile": str(row.get("normalization_profile") or "auto"),
                "normalization_config": normalization_config,
                "artifact_profile": artifact_profile,
                "run_dir": str((output_root / "runs" / run_id).resolve()),
            }
        )

    batch_id = output_root.name
    return {
        "schema_version": "v0.1.0",
        "manifest_path": str(manifest_path),
        "manifest_sha256": _hash_file(manifest_path),
        "artifact_profile": artifact_profile,
        "batch_id": batch_id,
        "output_root": str(output_root),
        "run_count": len(normalized_rows),
        "manifest_columns": [column for column in header if column],
        "rows": normalized_rows,
    }


def write_validated_manifest(payload: dict, outpath: str | Path) -> None:
    write_json(outpath, payload)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate and normalize a qPCR batch manifest.")
    parser.add_argument("--manifest", required=True, help="Input TSV manifest path.")
    parser.add_argument("--output-root", required=True, help="Batch output root directory.")
    parser.add_argument("--artifact-profile", choices=ARTIFACT_PROFILES, default="review")
    parser.add_argument("--out", required=True, help="Path for the normalized validated manifest JSON.")
    args = parser.parse_args(argv)

    payload = validate_manifest(args.manifest, args.output_root, artifact_profile=args.artifact_profile)
    write_validated_manifest(payload, args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
