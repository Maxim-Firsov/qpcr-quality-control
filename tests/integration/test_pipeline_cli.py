import csv
import json
from argparse import Namespace

import pytest

from src.cli import main, run_pipeline


def test_pipeline_cli_mode_writes_all_outputs(tmp_path):
    curve_csv = tmp_path / "curves.csv"
    with curve_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "run_id",
                "plate_id",
                "well_id",
                "sample_id",
                "target_id",
                "cycle",
                "fluorescence",
            ],
        )
        writer.writeheader()
        writer.writerows(
            [
                {
                    "run_id": "r1",
                    "plate_id": "p1",
                    "well_id": "A1",
                    "sample_id": "sample1",
                    "target_id": "target1",
                    "cycle": 1,
                    "fluorescence": 0.1,
                },
                {
                    "run_id": "r1",
                    "plate_id": "p1",
                    "well_id": "A1",
                    "sample_id": "sample1",
                    "target_id": "target1",
                    "cycle": 2,
                    "fluorescence": 0.5,
                },
                {
                    "run_id": "r1",
                    "plate_id": "p1",
                    "well_id": "A1",
                    "sample_id": "sample1",
                    "target_id": "target1",
                    "cycle": 3,
                    "fluorescence": 1.0,
                },
            ]
        )

    outdir = tmp_path / "out"
    run_pipeline(
        Namespace(
            curve_csv=str(curve_csv),
            rdml=None,
            plate_meta_csv=None,
            outdir=str(outdir),
            min_cycles=3,
            allow_empty_run=False,
            plate_schema="auto",
        )
    )

    assert (outdir / "well_calls.csv").exists()
    assert (outdir / "rerun_manifest.csv").exists()
    assert (outdir / "plate_qc_summary.json").exists()
    assert (outdir / "run_metadata.json").exists()
    assert (outdir / "summary.json").exists()
    assert (outdir / "report.html").exists()

    summary = json.loads((outdir / "plate_qc_summary.json").read_text(encoding="utf-8"))
    assert summary["schema_version"] == "v0.1.0"
    assert summary["generated_at_utc"].endswith("Z")

    metadata = json.loads((outdir / "run_metadata.json").read_text(encoding="utf-8"))
    assert metadata["timing_seconds"] >= 0.0
    assert metadata["peak_memory_mb"] >= 0.0
    assert "stage_timings_seconds" in metadata
    assert "warning_codes" in metadata
    assert metadata["input_snapshot_date"] != "1970-01-01"
    assert metadata["normalization"]["requested_profile"] == "auto"
    assert metadata["normalization"]["config_sha256"]

    run_summary = json.loads((outdir / "summary.json").read_text(encoding="utf-8"))
    assert run_summary["counts"]["well_calls"] == 1
    assert run_summary["global_counts"]["pass"] >= 0


def test_pipeline_raises_when_all_rows_are_rejected(tmp_path):
    curve_csv = tmp_path / "short.csv"
    with curve_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["run_id", "plate_id", "well_id", "sample_id", "target_id", "cycle", "fluorescence"],
        )
        writer.writeheader()
        writer.writerow(
            {
                "run_id": "r1",
                "plate_id": "p1",
                "well_id": "A1",
                "sample_id": "sample1",
                "target_id": "target1",
                "cycle": 1,
                "fluorescence": 0.1,
            }
        )

    with pytest.raises(ValueError, match="No eligible well-target curves remained after validation"):
        run_pipeline(
            Namespace(
                curve_csv=str(curve_csv),
                rdml=None,
                plate_meta_csv=None,
                outdir=str(tmp_path / "out"),
                min_cycles=3,
                allow_empty_run=False,
                plate_schema="auto",
            )
        )


def test_pipeline_can_emit_empty_outputs_when_allow_empty_run_is_enabled(tmp_path):
    curve_csv = tmp_path / "short.csv"
    with curve_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["run_id", "plate_id", "well_id", "sample_id", "target_id", "cycle", "fluorescence"],
        )
        writer.writeheader()
        writer.writerow(
            {
                "run_id": "r1",
                "plate_id": "p1",
                "well_id": "A1",
                "sample_id": "sample1",
                "target_id": "target1",
                "cycle": 1,
                "fluorescence": 0.1,
            }
        )

    summary = run_pipeline(
        Namespace(
            curve_csv=str(curve_csv),
            rdml=None,
            plate_meta_csv=None,
            outdir=str(tmp_path / "out"),
            min_cycles=3,
            allow_empty_run=True,
            plate_schema="auto",
        )
    )

    assert summary["well_calls"] == 0
    assert summary["rerun_manifest"] == 0
    assert summary["plate_count"] == 0


def test_main_returns_policy_failure_for_review_status(tmp_path):
    curve_csv = tmp_path / "curves.csv"
    with curve_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["run_id", "plate_id", "well_id", "sample_id", "target_id", "cycle", "fluorescence"],
        )
        writer.writeheader()
        writer.writerows(
            [
                {"run_id": "r1", "plate_id": "p1", "well_id": "A1", "sample_id": "sample1", "target_id": "target1", "cycle": 1, "fluorescence": 0.1},
                {"run_id": "r1", "plate_id": "p1", "well_id": "A1", "sample_id": "sample1", "target_id": "target1", "cycle": 2, "fluorescence": 0.2},
                {"run_id": "r1", "plate_id": "p1", "well_id": "A1", "sample_id": "sample1", "target_id": "target1", "cycle": 3, "fluorescence": 0.3},
            ]
        )

    code = main(
        [
            "--curve-csv",
            str(curve_csv),
            "--outdir",
            str(tmp_path / "out"),
            "--min-cycles",
            "3",
            "--fail-on-review",
        ]
    )
    assert code == 2


def test_main_batch_manifest_writes_batch_summary(tmp_path):
    curve_a = tmp_path / "curves_a.csv"
    curve_b = tmp_path / "curves_b.csv"
    for curve_path, terminal in [(curve_a, 0.3), (curve_b, 0.9)]:
        with curve_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["run_id", "plate_id", "well_id", "sample_id", "target_id", "cycle", "fluorescence"],
            )
            writer.writeheader()
            writer.writerows(
                [
                    {"run_id": "r1", "plate_id": "p1", "well_id": "A1", "sample_id": "sample1", "target_id": "target1", "cycle": 1, "fluorescence": 0.1},
                    {"run_id": "r1", "plate_id": "p1", "well_id": "A1", "sample_id": "sample1", "target_id": "target1", "cycle": 2, "fluorescence": 0.2},
                    {"run_id": "r1", "plate_id": "p1", "well_id": "A1", "sample_id": "sample1", "target_id": "target1", "cycle": 3, "fluorescence": terminal},
                ]
            )

    manifest = tmp_path / "batch.csv"
    with manifest.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["input_mode", "input_path", "outdir", "min_cycles", "plate_schema", "allow_empty_run"],
        )
        writer.writeheader()
        writer.writerow(
            {
                "input_mode": "curve_csv",
                "input_path": str(curve_a),
                "outdir": str(tmp_path / "run_a"),
                "min_cycles": 3,
                "plate_schema": "auto",
                "allow_empty_run": "false",
            }
        )
        writer.writerow(
            {
                "input_mode": "curve_csv",
                "input_path": str(curve_b),
                "outdir": str(tmp_path / "run_b"),
                "min_cycles": 3,
                "plate_schema": "auto",
                "allow_empty_run": "false",
            }
        )

    code = main(["--batch-manifest", str(manifest), "--outdir", str(tmp_path / "batch_out")])
    assert code == 0
    batch_summary = json.loads((tmp_path / "batch_out" / "batch_summary.json").read_text(encoding="utf-8"))
    assert batch_summary["run_count"] == 2
