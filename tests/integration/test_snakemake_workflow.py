import csv
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest


pytestmark = pytest.mark.skipif(importlib.util.find_spec("snakemake") is None, reason="snakemake is not installed")


def _write_curve_csv(path: Path, run_id: str, terminal_value: float) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["run_id", "plate_id", "well_id", "sample_id", "target_id", "cycle", "fluorescence"],
        )
        writer.writeheader()
        writer.writerows(
            [
                {"run_id": run_id, "plate_id": "p1", "well_id": "A1", "sample_id": "sample1", "target_id": "target1", "cycle": 1, "fluorescence": 0.1},
                {"run_id": run_id, "plate_id": "p1", "well_id": "A1", "sample_id": "sample1", "target_id": "target1", "cycle": 2, "fluorescence": 0.2},
                {"run_id": run_id, "plate_id": "p1", "well_id": "A1", "sample_id": "sample1", "target_id": "target1", "cycle": 3, "fluorescence": terminal_value},
            ]
        )


def test_snakemake_batch_generates_handoff_packet(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    pass_curve = tmp_path / "pass.csv"
    review_curve = tmp_path / "review.csv"
    _write_curve_csv(pass_curve, "pass_run", 1.0)
    _write_curve_csv(review_curve, "review_run", 0.3)

    manifest = tmp_path / "manifest.tsv"
    manifest.write_text(
        "run_id\tinput_mode\tinput_path\tmin_cycles\tplate_schema\tallow_empty_run\n"
        f"pass_run\tcurve_csv\t{pass_curve}\t3\tauto\tfalse\n"
        f"review_run\tcurve_csv\t{review_curve}\t3\tauto\tfalse\n",
        encoding="utf-8",
    )
    policy = tmp_path / "policy.yaml"
    policy.write_text(
        json.dumps(
            {
                "max_failed_runs_for_release": 0,
                "max_rerun_wells_for_release": 0,
                "max_review_wells_for_release": 0,
                "max_review_runs_for_release": 0,
            }
        ),
        encoding="utf-8",
    )
    config = tmp_path / "batch_config.yaml"
    config.write_text(
        json.dumps(
            {
                "manifest": str(manifest),
                "output_root": str(tmp_path / "batch_outputs"),
                "artifact_profile": "review",
                "gate_config": str(policy),
            }
        ),
        encoding="utf-8",
    )

    completed = subprocess.run(
        [sys.executable, "-m", "snakemake", "--snakefile", str(repo_root / "Snakefile"), "--cores", "1", "--configfile", str(config)],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    batch_out = tmp_path / "batch_outputs"
    batch_master = json.loads((batch_out / "batch_master.json").read_text(encoding="utf-8"))
    gate_status = json.loads((batch_out / "batch_gate_status.json").read_text(encoding="utf-8"))

    assert batch_master["run_count"] == 2
    assert gate_status["release_status"] in {"review", "block"}
    pass_record = next(record for record in batch_master["runs"] if record["run_id"] == "pass_run")
    review_record = next(record for record in batch_master["runs"] if record["run_id"] == "review_run")
    assert pass_record["artifact_inventory"]["report.html"]["generated"] is False
    assert pass_record["artifact_inventory"]["well_calls.csv"]["generated"] is False
    assert review_record["artifact_inventory"]["well_calls.csv"]["generated"] is True
    assert (batch_out / "batch_report.md").exists()
    assert (batch_out / "failure_reason_counts.tsv").exists()
