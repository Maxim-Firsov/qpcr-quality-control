import csv

from src.io.csv_loader import load_curve_csv, load_plate_meta_csv


def test_loaders_read_csv_shapes(tmp_path):
    curve = tmp_path / "curves.csv"
    with curve.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["run_id", "plate_id", "well_id", "sample_id", "target_id", "cycle", "fluorescence"])
        writer.writeheader()
        writer.writerow(
            {
                "run_id": "r1",
                "plate_id": "p1",
                "well_id": "A1",
                "sample_id": "s1",
                "target_id": "t1",
                "cycle": 1,
                "fluorescence": 0.1,
            }
        )
    meta = tmp_path / "meta.csv"
    with meta.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["plate_id", "well_id", "control_type"])
        writer.writeheader()
        writer.writerow({"plate_id": "p1", "well_id": "A01", "control_type": "sample"})

    curves = load_curve_csv(curve)
    plate_meta = load_plate_meta_csv(meta)
    assert len(curves) == 1
    assert plate_meta[("p1", "A01")]["control_type"] == "sample"


def test_plate_meta_loader_normalizes_short_well_ids(tmp_path):
    meta = tmp_path / "meta.csv"
    with meta.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["plate_id", "well_id", "control_type", "replicate_group"])
        writer.writeheader()
        writer.writerow({"plate_id": "p1", "well_id": "B3", "control_type": "ntc", "replicate_group": "rg1"})

    plate_meta = load_plate_meta_csv(meta)
    assert ("p1", "B03") in plate_meta
    assert plate_meta[("p1", "B03")]["well_id"] == "B03"
