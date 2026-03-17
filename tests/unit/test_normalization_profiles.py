import json

from src.core.normalization_profiles import load_normalization_profiles, resolve_normalization_profile


def test_load_normalization_profiles_reads_default_config():
    profiles = load_normalization_profiles()
    assert "default_profile" in profiles
    assert "profiles" in profiles
    assert "standard" in profiles["profiles"]


def test_resolve_normalization_profile_prefers_instrument_then_assay():
    profiles = {
        "default_profile": "standard",
        "profiles": {
            "standard": {"baseline_strategy": "minimum", "baseline_cycle_count": 3, "signal_scale": 1.0},
            "instrument_lc480": {"baseline_strategy": "mean_first_n", "baseline_cycle_count": 4},
            "assay_target_x": {"signal_scale": 1.5},
        },
        "instrument_profiles": {"roche lc480": "instrument_lc480"},
        "assay_profiles": {"target_x": "assay_target_x"},
    }

    resolved = resolve_normalization_profile(
        instrument="Roche LC480",
        target_id="target_x",
        profiles=profiles,
        requested_profile=None,
    )

    assert resolved["profile_name"] == "instrument_lc480+assay_target_x"
    assert resolved["baseline_strategy"] == "mean_first_n"
    assert resolved["baseline_cycle_count"] == 4
    assert resolved["signal_scale"] == 1.5


def test_resolve_normalization_profile_honors_explicit_request():
    profiles = {
        "default_profile": "standard",
        "profiles": {
            "standard": {"baseline_strategy": "minimum", "baseline_cycle_count": 3, "signal_scale": 1.0},
            "high_sensitivity": {"baseline_strategy": "median_first_n", "baseline_cycle_count": 5, "signal_scale": 1.2},
        },
    }

    resolved = resolve_normalization_profile(
        instrument="unknown",
        target_id="unknown",
        profiles=profiles,
        requested_profile="high_sensitivity",
    )

    assert resolved["profile_name"] == "high_sensitivity"
    assert resolved["baseline_strategy"] == "median_first_n"
    assert resolved["baseline_cycle_count"] == 5
    assert resolved["signal_scale"] == 1.2


def test_resolve_normalization_profile_rejects_unknown_explicit_profile():
    profiles = {
        "default_profile": "standard",
        "profiles": {"standard": {"baseline_strategy": "minimum", "baseline_cycle_count": 3, "signal_scale": 1.0}},
    }

    try:
        resolve_normalization_profile(
            instrument="unknown",
            target_id="unknown",
            profiles=profiles,
            requested_profile="missing_profile",
        )
    except ValueError as exc:
        assert "Unknown normalization profile" in str(exc)
    else:
        raise AssertionError("Expected ValueError for unknown explicit normalization profile")
