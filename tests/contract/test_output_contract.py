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
    run_pipeline(Namespace(curve_csv=str(curve_csv), plate_meta_csv=None, outdir=str(outdir), min_cycles=3))

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
