from src.core.normalize import normalize_rows


def test_normalize_rows_standardizes_well_and_types():
    rows = [
        {
            "run_id": "run1",
            "plate_id": "plateA",
            "well_id": "a1",
            "sample_id": "",
            "target_id": "",
            "cycle": "1",
            "fluorescence": "0.10",
        }
    ]
    out = normalize_rows(rows)
    assert out[0]["well_id"] == "A01"
    assert out[0]["sample_id"] == "unknown_sample"
    assert out[0]["target_id"] == "unknown_target"
    assert out[0]["cycle"] == 1
    assert out[0]["fluorescence"] == 0.10
