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


def test_build_features_applies_instrument_profile_override():
    rows = [
        {
            "run_id": "r1",
            "plate_id": "p1",
            "well_id": "A01",
            "sample_id": "s1",
            "target_id": "t1",
            "cycle": 1,
            "fluorescence": 1.0,
            "instrument": "Roche LC480",
        },
        {
            "run_id": "r1",
            "plate_id": "p1",
            "well_id": "A01",
            "sample_id": "s1",
            "target_id": "t1",
            "cycle": 2,
            "fluorescence": 1.2,
            "instrument": "Roche LC480",
        },
        {
            "run_id": "r1",
            "plate_id": "p1",
            "well_id": "A01",
            "sample_id": "s1",
            "target_id": "t1",
            "cycle": 3,
            "fluorescence": 1.4,
            "instrument": "Roche LC480",
        },
    ]

    out = build_features(rows)

    assert out[0]["normalization_profile"] == "roche_lc480_standard"
    assert out[0]["baseline_strategy"] == "median_first_n"
    assert round(out[0]["baseline_value"], 3) == 1.2
    assert round(out[2]["f_adj"], 3) == 0.21
