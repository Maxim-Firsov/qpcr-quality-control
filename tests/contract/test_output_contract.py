import csv
import json
from argparse import Namespace

from src.cli import run_pipeline


def _read_header(path):
    with path.open("r", encoding="utf-8", newline="") as handle:
        return next(csv.reader(handle))


def test_output_contract_required_columns_and_keys(tmp_path):
    curve_csv = tmp_path / "curves.csv"
    with curve_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["run_id", "plate_id", "well_id", "sample_id", "target_id", "cycle", "fluorescence"],
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
                    "fluorescence": 0.2,
                },
                {
                    "run_id": "r1",
                    "plate_id": "p1",
                    "well_id": "A1",
                    "sample_id": "sample1",
                    "target_id": "target1",
                    "cycle": 3,
                    "fluorescence": 0.3,
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

    well_header = _read_header(outdir / "well_calls.csv")
    assert set(
        [
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
    ).issubset(set(well_header))

    summary = json.loads((outdir / "plate_qc_summary.json").read_text(encoding="utf-8"))
    for key in ["schema_version", "generated_at_utc", "plates", "global_counts"]:
        assert key in summary

    run_summary = json.loads((outdir / "summary.json").read_text(encoding="utf-8"))
    for key in ["schema_version", "generated_at_utc", "execution_mode", "plate_schema", "counts", "global_counts", "timing_seconds", "peak_memory_mb", "warning_codes"]:
        assert key in run_summary

    metadata = json.loads((outdir / "run_metadata.json").read_text(encoding="utf-8"))
    assert "hash" in metadata["model_config"]
    assert metadata["plate_schema"] == "auto"
    assert "peak_memory_mb" in metadata
    assert "stage_timings_seconds" in metadata
    assert "warning_codes" in metadata
    for key in ["curve_csv_sha256", "rdml_sha256", "plate_meta_csv_sha256"]:
        assert key in metadata["input_hashes"]

    report_html = (outdir / "report.html").read_text(encoding="utf-8")
    assert "Overview" in report_html
    assert "Per-Plate Summary" in report_html
    assert "Rerun Rationale" in report_html
