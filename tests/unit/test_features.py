from src.core.features import build_features


def test_build_features_adds_derivatives():
    rows = [
        {
            "run_id": "r1",
            "plate_id": "p1",
            "well_id": "A01",
            "sample_id": "s1",
            "target_id": "t1",
            "cycle": 1,
            "fluorescence": 0.1,
        },
        {
            "run_id": "r1",
            "plate_id": "p1",
            "well_id": "A01",
            "sample_id": "s1",
            "target_id": "t1",
            "cycle": 2,
            "fluorescence": 0.4,
        },
    ]
    out = build_features(rows)
    assert out[0]["f_adj"] == 0.0
    assert out[1]["df"] == 0.30000000000000004
