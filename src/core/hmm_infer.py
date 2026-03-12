"""Deterministic HMM-like inference scaffold."""

from __future__ import annotations

import hashlib
from collections import defaultdict
from math import exp
from pathlib import Path
from typing import Iterable

STATE_BASELINE = "baseline_noise"
STATE_EXP = "exponential_amplification"
STATE_TRANSITION = "linear_transition"
STATE_PLATEAU = "plateau"
DEFAULT_MODEL_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "model_v1.yaml"
STATE_ORDER = [STATE_BASELINE, STATE_EXP, STATE_TRANSITION, STATE_PLATEAU]


def load_model_config(path: str | Path | None = None) -> dict:
    config_path = Path(path) if path else DEFAULT_MODEL_CONFIG_PATH
    text = config_path.read_text(encoding="utf-8")
    # Lightweight parser keeps runtime dependency-free while the config schema is simple.
    lines = [line.strip() for line in text.splitlines() if line.strip() and not line.strip().startswith("#")]
    exp_df_threshold = None
    plateau_df_threshold = None
    states: list[str] = []
    deterministic = False
    in_states = False

    for line in lines:
        if line.startswith("states:"):
            in_states = True
            continue
        if in_states and line.startswith("- "):
            states.append(line[2:].strip())
            continue
        if in_states and not line.startswith("- "):
            in_states = False
        if line.startswith("exp_df_threshold:"):
            exp_df_threshold = float(line.split(":", 1)[1].strip())
        elif line.startswith("plateau_df_threshold:"):
            plateau_df_threshold = float(line.split(":", 1)[1].strip())
        elif line.startswith("deterministic:"):
            deterministic = line.split(":", 1)[1].strip().lower() == "true"

    if exp_df_threshold is None or plateau_df_threshold is None:
        raise ValueError(f"Missing threshold values in model config: {config_path}")
    if not states:
        states = [STATE_BASELINE, STATE_EXP, STATE_TRANSITION, STATE_PLATEAU]

    return {
        "path": str(config_path),
        "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "states": states,
        "thresholds": {
            "exp_df_threshold": exp_df_threshold,
            "plateau_df_threshold": plateau_df_threshold,
        },
        "deterministic": deterministic,
    }


def _state_from_features(feature_row: dict, exp_df_threshold: float, plateau_df_threshold: float) -> str:
    df = float(feature_row["df"])
    d2f = float(feature_row["d2f"])
    if df >= exp_df_threshold and d2f >= 0:
        return STATE_EXP
    if df >= plateau_df_threshold:
        return STATE_TRANSITION
    if df >= 0 and d2f < 0:
        return STATE_PLATEAU
    return STATE_BASELINE


def _emission_score(feature_row: dict, state: str, exp_df_threshold: float, plateau_df_threshold: float) -> float:
    df = float(feature_row["df"])
    d2f = float(feature_row["d2f"])
    f_adj = float(feature_row.get("f_adj", 0.0))

    if state == STATE_BASELINE:
        penalty = abs(min(df, exp_df_threshold)) + max(0.0, df - plateau_df_threshold) + max(0.0, f_adj - 0.15)
        return 1.2 - (penalty * 10.0)
    if state == STATE_EXP:
        score = 1.0 + (df - exp_df_threshold) * 8.0
        score += max(0.0, d2f) * 4.0
        score -= max(0.0, -d2f) * 2.0
        return score
    if state == STATE_TRANSITION:
        distance = abs(df - plateau_df_threshold)
        score = 0.9 - distance * 6.0
        score += max(0.0, f_adj - 0.1) * 1.5
        return score

    score = 0.8 + max(0.0, -d2f) * 4.0 + max(0.0, f_adj - 0.2) * 2.0
    score -= max(0.0, df - exp_df_threshold) * 3.0
    return score


def _allowed_previous_states(states: list[str], current_index: int) -> list[str]:
    previous = [states[current_index]]
    if current_index > 0:
        previous.append(states[current_index - 1])
    return previous


def _transition_bonus(prev_state: str, current_state: str, states: list[str]) -> float:
    prev_index = states.index(prev_state)
    current_index = states.index(current_state)
    if prev_index == current_index:
        return 0.25
    if current_index == prev_index + 1:
        return 0.0
    return -9999.0


def _margin_confidence(scores: dict[str, float], winning_state: str) -> float:
    ordered = sorted(scores.values(), reverse=True)
    if len(ordered) < 2:
        return 1.0
    margin = ordered[0] - ordered[1]
    return round(1.0 / (1.0 + exp(-margin)), 6)


def _decode_rows(rows: list[dict], exp_df_threshold: float, plateau_df_threshold: float) -> list[dict]:
    states = STATE_ORDER
    emission_tables = [
        {
            state: _emission_score(row, state, exp_df_threshold, plateau_df_threshold)
            for state in states
        }
        for row in rows
    ]

    path_scores: list[dict[str, float]] = []
    backpointers: list[dict[str, str | None]] = []
    start_scores = {state: -9999.0 for state in states}
    start_scores[STATE_BASELINE] = emission_tables[0][STATE_BASELINE]
    path_scores.append(start_scores)
    backpointers.append({state: None for state in states})

    for cycle_index in range(1, len(rows)):
        current_scores: dict[str, float] = {}
        current_backpointers: dict[str, str] = {}
        for state_index, state in enumerate(states):
            candidates: list[tuple[float, str]] = []
            for prev_state in _allowed_previous_states(states, state_index):
                candidate_score = (
                    path_scores[cycle_index - 1][prev_state]
                    + _transition_bonus(prev_state, state, states)
                    + emission_tables[cycle_index][state]
                )
                candidates.append((candidate_score, prev_state))
            best_score, best_prev_state = max(candidates, key=lambda item: item[0])
            current_scores[state] = best_score
            current_backpointers[state] = best_prev_state
        path_scores.append(current_scores)
        backpointers.append(current_backpointers)

    final_state = max(states, key=lambda state: path_scores[-1][state])
    state_path = [final_state]
    for cycle_index in range(len(rows) - 1, 0, -1):
        final_state = backpointers[cycle_index][final_state]
        state_path.append(final_state)
    state_path.reverse()

    decoded: list[dict] = []
    for index, row in enumerate(rows):
        out = dict(row)
        out["state"] = state_path[index]
        out["state_confidence"] = _margin_confidence(emission_tables[index], state_path[index])
        decoded.append(out)
    return decoded


def infer_state_paths(
    feature_rows: Iterable[dict],
    exp_df_threshold: float | None = None,
    plateau_df_threshold: float | None = None,
    model_config_path: str | Path | None = None,
) -> list[dict]:
    if exp_df_threshold is None or plateau_df_threshold is None:
        config = load_model_config(model_config_path)
        exp_df_threshold = config["thresholds"]["exp_df_threshold"]
        plateau_df_threshold = config["thresholds"]["plateau_df_threshold"]

    grouped: dict[tuple[str, str, str, str], list[dict]] = defaultdict(list)
    for row in feature_rows:
        key = (row["run_id"], row["plate_id"], row["well_id"], row["target_id"])
        grouped[key].append(row)

    inferred: list[dict] = []
    for _, rows in grouped.items():
        ordered = sorted(rows, key=lambda r: r["cycle"])
        inferred.extend(_decode_rows(ordered, exp_df_threshold, plateau_df_threshold))
    inferred.sort(
        key=lambda r: (
            r["run_id"],
            r["plate_id"],
            r["well_id"],
            r["target_id"],
            r["cycle"],
        )
    )
    return inferred
