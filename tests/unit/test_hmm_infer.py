from src.core.hmm_infer import infer_state_paths, load_model_config


def test_infer_state_paths_emits_state_for_each_row():
    features = [
        {
            "run_id": "r1",
            "plate_id": "p1",
            "well_id": "A01",
            "sample_id": "s1",
            "target_id": "t1",
            "cycle": 1,
            "df": 0.0,
            "d2f": 0.0,
        },
        {
            "run_id": "r1",
            "plate_id": "p1",
            "well_id": "A01",
            "sample_id": "s1",
            "target_id": "t1",
            "cycle": 2,
            "df": 0.2,
            "d2f": 0.2,
        },
    ]
    out = infer_state_paths(features)
    assert len(out) == 2
    assert all("state" in row for row in out)


def test_infer_state_paths_is_deterministic_for_same_input():
    features = [
        {
            "run_id": "r1",
            "plate_id": "p1",
            "well_id": "A01",
            "sample_id": "s1",
            "target_id": "t1",
            "cycle": 1,
            "df": 0.0,
            "d2f": 0.0,
        },
        {
            "run_id": "r1",
            "plate_id": "p1",
            "well_id": "A01",
            "sample_id": "s1",
            "target_id": "t1",
            "cycle": 2,
            "df": 0.2,
            "d2f": 0.1,
        },
    ]
    out_a = infer_state_paths(features)
    out_b = infer_state_paths(features)
    assert out_a == out_b


def test_infer_state_paths_follows_forward_only_state_progression():
    features = [
        {"run_id": "r1", "plate_id": "p1", "well_id": "A01", "sample_id": "s1", "target_id": "t1", "cycle": 1, "f_adj": 0.0, "df": 0.0, "d2f": 0.0},
        {"run_id": "r1", "plate_id": "p1", "well_id": "A01", "sample_id": "s1", "target_id": "t1", "cycle": 2, "f_adj": 0.05, "df": 0.04, "d2f": 0.04},
        {"run_id": "r1", "plate_id": "p1", "well_id": "A01", "sample_id": "s1", "target_id": "t1", "cycle": 3, "f_adj": 0.25, "df": 0.18, "d2f": 0.14},
        {"run_id": "r1", "plate_id": "p1", "well_id": "A01", "sample_id": "s1", "target_id": "t1", "cycle": 4, "f_adj": 0.42, "df": 0.06, "d2f": -0.12},
    ]
    out = infer_state_paths(features)
    states = [row["state"] for row in out]
    ordering = {
        "baseline_noise": 0,
        "exponential_amplification": 1,
        "linear_transition": 2,
        "plateau": 3,
    }
    assert states[0] == "baseline_noise"
    assert states[2] == "exponential_amplification"
    assert ordering[states[3]] >= ordering[states[2]]
    assert [ordering[state] for state in states] == sorted(ordering[state] for state in states)
    assert all(0.0 <= row["state_confidence"] <= 1.0 for row in out)


def test_load_model_config_reads_locked_thresholds():
    config = load_model_config()
    assert config["thresholds"]["exp_df_threshold"] == 0.12
    assert config["thresholds"]["plateau_df_threshold"] == 0.03
    assert config["deterministic"] is True
