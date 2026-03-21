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


def _run_snakemake(repo_root: Path, config: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "snakemake", "--snakefile", str(repo_root / "Snakefile"), "--cores", "1", "--configfile", str(config)],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
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
        "max_failed_runs_for_release: 0\n"
        "max_rerun_wells_for_release: 0\n"
        "max_review_wells_for_release: 0\n"
        "max_review_runs_for_release: 0\n",
        encoding="utf-8",
    )
    config = tmp_path / "batch_config.yaml"
    config.write_text(
        f"manifest: {manifest.as_posix()}\n"
        f"output_root: {(tmp_path / 'batch_outputs').as_posix()}\n"
        "artifact_profile: review\n"
        f"gate_config: {policy.as_posix()}\n",
        encoding="utf-8",
    )

    completed = _run_snakemake(repo_root, config)

    assert completed.returncode == 0, completed.stderr
    batch_out = tmp_path / "batch_outputs"
    batch_master = json.loads((batch_out / "batch_master.json").read_text(encoding="utf-8"))
    gate_status = json.loads((batch_out / "batch_gate_status.json").read_text(encoding="utf-8"))

    assert batch_master["run_count"] == 2
    assert gate_status["release_status"] in {"review", "block"}
    pass_record = next(record for record in batch_master["runs"] if record["run_id"] == "pass_run")
    review_record = next(record for record in batch_master["runs"] if record["run_id"] == "review_run")
    assert pass_record["artifact_inventory"]["report.html"]["generated"] is True
    assert pass_record["artifact_inventory"]["well_calls.csv"]["generated"] is True
    assert pass_record["artifact_inventory"]["report.html"]["reason"] == "workflow_tracked_report_html"
    assert pass_record["artifact_inventory"]["well_calls.csv"]["reason"] == "workflow_tracked_well_calls"
    assert review_record["artifact_inventory"]["well_calls.csv"]["generated"] is True
    assert (batch_out / "batch_report.md").exists()
    assert (batch_out / "failure_reason_counts.tsv").exists()


def test_snakemake_invalid_manifest_writes_validation_artifact_and_stops(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    manifest = tmp_path / "manifest.tsv"
    manifest.write_text(
        "run_id\tinput_mode\tinput_path\n"
        "bad_run\tcurve_csv\tmissing.csv\n",
        encoding="utf-8",
    )
    config = tmp_path / "batch_config.yaml"
    config.write_text(
        f"manifest: {manifest.as_posix()}\n"
        f"output_root: {(tmp_path / 'batch_outputs').as_posix()}\n"
        "artifact_profile: review\n",
        encoding="utf-8",
    )

    completed = _run_snakemake(repo_root, config)

    assert completed.returncode != 0
    validated_manifest = tmp_path / "batch_outputs" / "_workflow" / "validated_manifest.json"
    assert validated_manifest.exists()
    payload = json.loads(validated_manifest.read_text(encoding="utf-8"))
    assert payload["validation_status"] == "invalid"
    assert payload["errors"]
    assert not any((tmp_path / "batch_outputs" / "runs").glob("*"))


def test_snakemake_rerun_restores_tracked_compact_outputs(tmp_path):
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
        "max_failed_runs_for_release: 0\n"
        "max_rerun_wells_for_release: 0\n"
        "max_review_wells_for_release: 0\n"
        "max_review_runs_for_release: 0\n",
        encoding="utf-8",
    )
    config = tmp_path / "batch_config.yaml"
    config.write_text(
        f"manifest: {manifest.as_posix()}\n"
        f"output_root: {(tmp_path / 'batch_outputs').as_posix()}\n"
        "artifact_profile: review\n"
        f"gate_config: {policy.as_posix()}\n",
        encoding="utf-8",
    )

    first_run = _run_snakemake(repo_root, config)
    assert first_run.returncode == 0, first_run.stderr

    batch_out = tmp_path / "batch_outputs"
    tracked_files = [
        batch_out / "runs" / "review_run" / "run_metadata.json",
        batch_out / "runs" / "review_run" / "plate_qc_summary.json",
    ]
    rerun_manifest = batch_out / "runs" / "review_run" / "rerun_manifest.csv"
    rerun_manifest.write_text(
        "plate_id,well_id,target_id,sample_id,rerun_reason,evidence_score,recommended_action\n"
        "p1,Z99,bogus,bogus_sample,manual_tamper,1.0,do_not_keep\n",
        encoding="utf-8",
    )
    for tracked_file in tracked_files:
        tracked_file.unlink()

    second_run = _run_snakemake(repo_root, config)
    assert second_run.returncode == 0, second_run.stderr
    assert rerun_manifest.exists()
    for tracked_file in tracked_files:
        assert tracked_file.exists()

    rerun_queue = (batch_out / "rerun_queue.csv").read_text(encoding="utf-8")
    assert "manual_tamper" not in rerun_queue
    assert "bogus_sample" not in rerun_queue


def test_snakemake_rerun_restores_tracked_reviewer_artifacts(tmp_path):
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
    config = tmp_path / "batch_config.yaml"
    config.write_text(
        f"manifest: {manifest.as_posix()}\n"
        f"output_root: {(tmp_path / 'batch_outputs').as_posix()}\n"
        "artifact_profile: review\n",
        encoding="utf-8",
    )

    first_run = _run_snakemake(repo_root, config)
    assert first_run.returncode == 0, first_run.stderr

    batch_out = tmp_path / "batch_outputs"
    review_well_calls = batch_out / "runs" / "review_run" / "well_calls.csv"
    review_report = batch_out / "runs" / "review_run" / "report.html"
    pass_well_calls = batch_out / "runs" / "pass_run" / "well_calls.csv"
    pass_report = batch_out / "runs" / "pass_run" / "report.html"
    for artifact in [review_well_calls, review_report, pass_well_calls, pass_report]:
        artifact.unlink()

    second_run = _run_snakemake(repo_root, config)
    assert second_run.returncode == 0, second_run.stderr
    for artifact in [review_well_calls, review_report, pass_well_calls, pass_report]:
        assert artifact.exists()


def test_snakemake_preserves_failed_run_placeholders_for_analysis_errors(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    short_curve = tmp_path / "short.csv"
    with short_curve.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["run_id", "plate_id", "well_id", "sample_id", "target_id", "cycle", "fluorescence"],
        )
        writer.writeheader()
        writer.writerow(
            {
                "run_id": "failed_run",
                "plate_id": "p1",
                "well_id": "A1",
                "sample_id": "sample1",
                "target_id": "target1",
                "cycle": 1,
                "fluorescence": 0.1,
            }
        )

    manifest = tmp_path / "manifest.tsv"
    manifest.write_text(
        "run_id\tinput_mode\tinput_path\tmin_cycles\tplate_schema\tallow_empty_run\n"
        f"failed_run\tcurve_csv\t{short_curve}\t3\tauto\tfalse\n",
        encoding="utf-8",
    )
    config = tmp_path / "batch_config.yaml"
    config.write_text(
        f"manifest: {manifest.as_posix()}\n"
        f"output_root: {(tmp_path / 'batch_outputs').as_posix()}\n"
        "artifact_profile: review\n",
        encoding="utf-8",
    )

    completed = _run_snakemake(repo_root, config)
    assert completed.returncode == 0, completed.stderr

    batch_out = tmp_path / "batch_outputs"
    run_dir = batch_out / "runs" / "failed_run"
    for expected in [
        run_dir / "summary.json",
        run_dir / "run_metadata.json",
        run_dir / "plate_qc_summary.json",
        run_dir / "rerun_manifest.csv",
        run_dir / "workflow_status.json",
    ]:
        assert expected.exists()

    batch_master = json.loads((batch_out / "batch_master.json").read_text(encoding="utf-8"))
    failed_record = batch_master["runs"][0]
    assert failed_record["execution_status"] == "failed"
    assert failed_record["run_status"] == "unavailable"
    assert failed_record["artifact_inventory"]["well_calls.csv"]["generated"] is True
    assert failed_record["artifact_inventory"]["report.html"]["generated"] is True

    gate_status = json.loads((batch_out / "batch_gate_status.json").read_text(encoding="utf-8"))
    assert gate_status["release_status"] == "block"
    assert "execution_failures_present" in gate_status["blocking_reasons"]
