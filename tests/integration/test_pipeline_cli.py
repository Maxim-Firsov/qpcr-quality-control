import csv
import json
from argparse import Namespace
from io import StringIO
from contextlib import redirect_stdout

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
    assert metadata["run_id"] == "r1"
    assert metadata["artifact_profile"] == "full"
    assert metadata["normalization"]["requested_profile"] == "auto"
    assert metadata["normalization"]["config_sha256"]
    assert metadata["control_map"]["config_path"] == ""
    assert metadata["melt_qc"]["well_target_count"] == 0
    assert metadata["qc_thresholds"]["replicate_ct_spread_threshold"] == 2.0
    assert metadata["qc_thresholds"]["replicate_ct_outlier_threshold"] == 1.5

    run_summary = json.loads((outdir / "summary.json").read_text(encoding="utf-8"))
    assert run_summary["run_id"] == "r1"
    assert run_summary["execution_status"] == "succeeded"
    assert run_summary["artifact_profile"] == "full"
    assert run_summary["run_status"] in {"pass", "review", "rerun"}
    assert run_summary["counts"]["well_calls"] == 1
    assert run_summary["counts"]["well_calls_written"] == 1
    assert run_summary["global_counts"]["pass"] >= 0
    assert run_summary["artifact_inventory"]["report.html"]["generated"] is True
    report_html = (outdir / "report.html").read_text(encoding="utf-8")
    assert "Plate Heatmaps" in report_html
    assert "Curve Drilldowns" in report_html


def test_pipeline_control_map_config_marks_controls(tmp_path):
    curve_csv = tmp_path / "curves.csv"
    with curve_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["run_id", "plate_id", "well_id", "sample_id", "target_id", "cycle", "fluorescence"],
        )
        writer.writeheader()
        writer.writerows(
            [
                {"run_id": "r1", "plate_id": "p1", "well_id": "A1", "sample_id": "ctrl", "target_id": "assay_a", "cycle": 1, "fluorescence": 0.1},
                {"run_id": "r1", "plate_id": "p1", "well_id": "A1", "sample_id": "ctrl", "target_id": "assay_a", "cycle": 2, "fluorescence": 0.5},
                {"run_id": "r1", "plate_id": "p1", "well_id": "A1", "sample_id": "ctrl", "target_id": "assay_a", "cycle": 3, "fluorescence": 1.0},
            ]
        )

    control_map = tmp_path / "control_map.json"
    control_map.write_text(
        json.dumps(
            {
                "rules": [
                    {
                        "plate_id": "*",
                        "well_ids": ["A01"],
                        "control_type": "positive_control",
                        "expected_target_id": "assay_a",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    outdir = tmp_path / "out"
    run_pipeline(
        Namespace(
            curve_csv=str(curve_csv),
            rdml=None,
            plate_meta_csv=None,
            control_map_config=str(control_map),
            outdir=str(outdir),
            min_cycles=3,
            allow_empty_run=False,
            plate_schema="auto",
        )
    )

    with (outdir / "well_calls.csv").open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["control_type"] == "positive_control"

    metadata = json.loads((outdir / "run_metadata.json").read_text(encoding="utf-8"))
    assert metadata["control_map"]["config_sha256"]


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


def test_main_prints_success_summary_for_single_run(tmp_path):
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
                {"run_id": "r1", "plate_id": "p1", "well_id": "A1", "sample_id": "sample1", "target_id": "target1", "cycle": 2, "fluorescence": 0.5},
                {"run_id": "r1", "plate_id": "p1", "well_id": "A1", "sample_id": "sample1", "target_id": "target1", "cycle": 3, "fluorescence": 1.0},
            ]
        )

    stdout = StringIO()
    with redirect_stdout(stdout):
        code = main(["--curve-csv", str(curve_csv), "--outdir", str(tmp_path / "out"), "--min-cycles", "3"])

    assert code == 0
    output = stdout.getvalue()
    assert "qpcr-quality-control completed:" in output
    assert "Summary:" in output


def test_main_batch_manifest_propagates_threshold_overrides(tmp_path):
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
                "input_path": str(curve_csv),
                "outdir": str(tmp_path / "run_a"),
                "min_cycles": 3,
                "plate_schema": "auto",
                "allow_empty_run": "false",
            }
        )

    code = main(
        [
            "--batch-manifest",
            str(manifest),
            "--outdir",
            str(tmp_path / "batch_out"),
            "--confidence-threshold",
            "0.9",
            "--late-ct-threshold",
            "22",
            "--low-signal-threshold",
            "0.99",
        ]
    )

    assert code == 0
    metadata = json.loads((tmp_path / "run_a" / "run_metadata.json").read_text(encoding="utf-8"))
    assert metadata["qc_thresholds"]["confidence_threshold"] == 0.9
    assert metadata["qc_thresholds"]["late_ct_threshold"] == 22.0
    assert metadata["qc_thresholds"]["low_signal_threshold"] == 0.99


def test_main_batch_manifest_accepts_utf8_bom_csv(tmp_path):
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
                {"run_id": "r1", "plate_id": "p1", "well_id": "A1", "sample_id": "sample1", "target_id": "target1", "cycle": 3, "fluorescence": 0.8},
            ]
        )

    manifest = tmp_path / "batch_bom.csv"
    manifest.write_text(
        "input_mode,input_path,outdir,min_cycles,plate_schema,allow_empty_run\n"
        f"curve_csv,{curve_csv},{tmp_path / 'run_a'},3,auto,false\n",
        encoding="utf-8-sig",
    )

    code = main(["--batch-manifest", str(manifest), "--outdir", str(tmp_path / "batch_out")])

    assert code == 0
    assert (tmp_path / "run_a" / "summary.json").exists()


def test_run_pipeline_review_artifact_profile_skips_heavy_outputs_for_pass_run(tmp_path):
    curve_csv = tmp_path / "curves.csv"
    with curve_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["run_id", "plate_id", "well_id", "sample_id", "target_id", "cycle", "fluorescence"],
        )
        writer.writeheader()
        writer.writerows(
            [
                {"run_id": "run_pass", "plate_id": "p1", "well_id": "A1", "sample_id": "sample1", "target_id": "target1", "cycle": 1, "fluorescence": 0.1},
                {"run_id": "run_pass", "plate_id": "p1", "well_id": "A1", "sample_id": "sample1", "target_id": "target1", "cycle": 2, "fluorescence": 0.5},
                {"run_id": "run_pass", "plate_id": "p1", "well_id": "A1", "sample_id": "sample1", "target_id": "target1", "cycle": 3, "fluorescence": 1.0},
            ]
        )

    outdir = tmp_path / "out"
    result = run_pipeline(
        Namespace(
            curve_csv=str(curve_csv),
            rdml=None,
            plate_meta_csv=None,
            outdir=str(outdir),
            min_cycles=3,
            allow_empty_run=False,
            plate_schema="auto",
            artifact_profile="review",
        )
    )

    assert result["artifact_profile"] == "review"
    assert result["run_status"] == "pass"
    assert not (outdir / "well_calls.csv").exists()
    assert not (outdir / "report.html").exists()
    summary = json.loads((outdir / "summary.json").read_text(encoding="utf-8"))
    assert summary["artifact_inventory"]["well_calls.csv"]["generated"] is False
    assert summary["artifact_inventory"]["report.html"]["generated"] is False
