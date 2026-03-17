"""Normalization profile helpers for assay- and instrument-aware feature transforms."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

DEFAULT_NORMALIZATION_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "normalization_profiles.json"


def load_normalization_profiles(path: str | Path | None = None) -> dict:
    config_path = Path(path) if path else DEFAULT_NORMALIZATION_CONFIG_PATH
    text = config_path.read_text(encoding="utf-8")
    profiles = json.loads(text)
    profiles["_path"] = str(config_path)
    profiles["_sha256"] = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return profiles


def _normalize_lookup_key(value: str) -> str:
    return " ".join(str(value or "").strip().lower().replace("_", " ").split())


def _normalized_mapping(mapping: dict[str, str]) -> dict[str, str]:
    return {_normalize_lookup_key(key): value for key, value in mapping.items()}


def resolve_normalization_profile(
    instrument: str,
    target_id: str,
    profiles: dict,
    requested_profile: str | None = None,
) -> dict:
    available_profiles = dict(profiles.get("profiles", {}))
    default_profile = str(profiles.get("default_profile", "standard"))
    instrument_profiles = _normalized_mapping(dict(profiles.get("instrument_profiles", {})))
    assay_profiles = _normalized_mapping(dict(profiles.get("assay_profiles", {})))

    if requested_profile:
        if requested_profile not in available_profiles:
            raise ValueError(f"Unknown normalization profile: {requested_profile}")
        resolved = dict(available_profiles[requested_profile])
        resolved["profile_name"] = requested_profile
        return resolved

    if default_profile not in available_profiles:
        raise ValueError(f"Default normalization profile is missing: {default_profile}")
    resolved = dict(available_profiles[default_profile])
    profile_name = default_profile

    instrument_key = _normalize_lookup_key(instrument)
    instrument_profile_name = instrument_profiles.get(instrument_key)
    if instrument_profile_name:
        resolved.update(available_profiles[instrument_profile_name])
        profile_name = instrument_profile_name

    assay_key = _normalize_lookup_key(target_id)
    assay_profile_name = assay_profiles.get(assay_key)
    if assay_profile_name:
        resolved.update(available_profiles[assay_profile_name])
        profile_name = assay_profile_name if not instrument_profile_name else f"{instrument_profile_name}+{assay_profile_name}"

    resolved["profile_name"] = profile_name
    return resolved
