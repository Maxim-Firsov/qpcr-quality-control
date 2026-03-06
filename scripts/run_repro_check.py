"""Deterministic output smoke check for the scaffold pipeline."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
import sys
import tempfile
from argparse import Namespace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.cli import run_pipeline


def _hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _make_fixture(path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["run_id", "plate_id", "well_id", "sample_id", "target_id", "cycle", "fluorescence"],
        )
        writer.writeheader()
        writer.writerows(
            [
                {"run_id": "r1", "plate_id": "p1", "well_id": "A1", "sample_id": "s1", "target_id": "t1", "cycle": 1, "fluorescence": 0.1},
                {"run_id": "r1", "plate_id": "p1", "well_id": "A1", "sample_id": "s1", "target_id": "t1", "cycle": 2, "fluorescence": 0.3},
                {"run_id": "r1", "plate_id": "p1", "well_id": "A1", "sample_id": "s1", "target_id": "t1", "cycle": 3, "fluorescence": 0.7},
            ]
        )


def main() -> int:
    if os.name == "nt":
        preferred_root = Path("C:/Users/max/AppData/Roaming/Python/Python313/pytest-tmp")
    else:
        preferred_root = Path(tempfile.gettempdir()) / "pytest-tmp"
    preferred_root.mkdir(parents=True, exist_ok=True)
    temp_dir = Path(tempfile.mkdtemp(prefix="qpcr_hmm_repro_", dir=str(preferred_root)))
    try:
        curve = temp_dir / "curves.csv"
        _make_fixture(curve)
        out1 = temp_dir / "out1"
        out2 = temp_dir / "out2"
        run_pipeline(Namespace(curve_csv=str(curve), plate_meta_csv=None, outdir=str(out1), min_cycles=3))
        run_pipeline(Namespace(curve_csv=str(curve), plate_meta_csv=None, outdir=str(out2), min_cycles=3))

        deterministic_files = ["well_calls.csv", "rerun_manifest.csv", "plate_qc_summary.json", "run_metadata.json"]
        for name in deterministic_files:
            if _hash_file(out1 / name) != _hash_file(out2 / name):
                print(json.dumps({"status": "fail", "file": name}))
                return 1

        print(json.dumps({"status": "ok"}))
        return 0
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
