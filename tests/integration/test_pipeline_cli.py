import csv
import json
from argparse import Namespace

from src.cli import run_pipeline


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
    run_pipeline(Namespace(curve_csv=str(curve_csv), plate_meta_csv=None, outdir=str(outdir), min_cycles=3))

    assert (outdir / "well_calls.csv").exists()
    assert (outdir / "rerun_manifest.csv").exists()
    assert (outdir / "plate_qc_summary.json").exists()
    assert (outdir / "run_metadata.json").exists()
    assert (outdir / "report.html").exists()

    summary = json.loads((outdir / "plate_qc_summary.json").read_text(encoding="utf-8"))
    assert summary["schema_version"] == "v0.1.0"
    assert summary["generated_at_utc"].endswith("Z")

    metadata = json.loads((outdir / "run_metadata.json").read_text(encoding="utf-8"))
    assert metadata["timing_seconds"] >= 0.0
    assert metadata["input_snapshot_date"] != "1970-01-01"
