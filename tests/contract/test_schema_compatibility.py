import csv
import json
from argparse import Namespace

from src.cli import run_pipeline


def test_v010_output_schema_compatibility(tmp_path):
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
                {"run_id": "r1", "plate_id": "p1", "well_id": "A1", "sample_id": "sample1", "target_id": "target1", "cycle": 2, "fluorescence": 0.4},
                {"run_id": "r1", "plate_id": "p1", "well_id": "A1", "sample_id": "sample1", "target_id": "target1", "cycle": 3, "fluorescence": 0.8},
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
            confidence_threshold=0.6,
            late_ct_threshold=35.0,
            low_signal_threshold=0.15,
        )
    )

    with (outdir / "well_calls.csv").open("r", encoding="utf-8", newline="") as handle:
        header = next(csv.reader(handle))
    assert header == [
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

    summary = json.loads((outdir / "summary.json").read_text(encoding="utf-8"))
    assert sorted(summary.keys()) == [
        "counts",
        "execution_mode",
        "generated_at_utc",
        "global_counts",
        "peak_memory_mb",
        "plate_schema",
        "schema_version",
        "timing_seconds",
        "warning_codes",
    ]

    metadata = json.loads((outdir / "run_metadata.json").read_text(encoding="utf-8"))
    assert sorted(metadata.keys()) == [
        "data_validation_summary",
        "execution_mode",
        "input_hashes",
        "input_snapshot_date",
        "inputs",
        "model_config",
        "normalization",
        "peak_memory_mb",
        "plate_schema",
        "qc_thresholds",
        "record_counts",
        "schema_version",
        "stage_timings_seconds",
        "timing_seconds",
        "tool_version",
        "warning_codes",
        "warnings",
    ]
    assert sorted(metadata["normalization"].keys()) == [
        "config_path",
        "config_sha256",
        "requested_profile",
    ]
